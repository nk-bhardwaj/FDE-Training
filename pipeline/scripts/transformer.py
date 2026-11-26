"""Transformer for the Online Retail II dataset.

Reads the cleaned CSV, renames columns to the warehouse target schema
(``pipeline/docs/schema-design.md`` Section 2), converts types, derives
``invoice_date`` / ``line_total`` / ``invoice_month``, and writes transformed
and rejected outputs plus a JSON report.

Validation performed here enforces the warehouse column domains:

* ``source_row_id``  -> positive BIGINT integer, unique across the input dataset.
* ``quantity``       -> BIGINT integer range.
* ``price``          -> NUMERIC(12,4), finite, exact scale/precision.
* ``line_total``     -> NUMERIC(14,4), finite, exact scale/precision.
* ``invoice_timestamp`` -> parsed, timezone-naive (timezone-aware values rejected).

Monetary values use :class:`decimal.Decimal` to avoid binary floating-point
arithmetic. This module is independent of Airflow and PostgreSQL.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Repository root and paths (relative to __file__, not cwd)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # .../fde-ai-sprint

CLEANED_INPUT = REPO_ROOT / "pipeline" / "data" / "cleaned" / "online_retail_II_cleaned.csv"

TRANSFORMED_PATH = REPO_ROOT / "pipeline" / "data" / "cleaned" / "online_retail_II_transformed.csv"

REJECTED_PATH = REPO_ROOT / "pipeline" / "data" / "rejected" / "online_retail_II_rejected.csv"

REPORT_PATH = (
    REPO_ROOT / "pipeline" / "data" / "profiles" / "online_retail_II_transformation_report.json"
)

# ---------------------------------------------------------------------------
# Column definitions (from schema-design.md Section 2)
# ---------------------------------------------------------------------------

# Input columns expected in the cleaned CSV (8 source + source_row_id).
EXPECTED_INPUT_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
    "source_row_id",
]

# Output columns for the transformed CSV (warehouse target names + derived).
TRANSFORMED_COLUMNS = [
    "source_row_id",
    "invoice",
    "stock_code",
    "description",
    "quantity",
    "invoice_timestamp",
    "price",
    "customer_id",
    "country",
    "invoice_date",
    "line_total",
    "invoice_month",
]

# Fields that must be present (NOT NULL in the warehouse schema).
REQUIRED_FIELDS = ["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price", "Country"]

# ---------------------------------------------------------------------------
# Numeric domain constants (mirror the PostgreSQL target schema)
# ---------------------------------------------------------------------------

BIGINT_MIN = -(2**63)
BIGINT_MAX = 2**63 - 1

PRICE_PRECISION = 12
PRICE_SCALE = 4

LINE_TOTAL_PRECISION = 14
LINE_TOTAL_SCALE = 4


# ---------------------------------------------------------------------------
# Low-level parsing helpers
# ---------------------------------------------------------------------------


def _is_missing(value: Any) -> bool:
    """Return True if *value* is None, NaN/NA, or an empty/whitespace string."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _trim(value: Any) -> str | None:
    """Trim leading/trailing whitespace; return None for missing values."""
    if _is_missing(value):
        return None
    return str(value).strip()


def _to_decimal(value: Any) -> Decimal:
    """Convert *value* to a Decimal without going through float arithmetic."""
    return Decimal(str(value).strip())


def _fits_numeric(value: Decimal, precision: int, scale: int) -> bool:
    """Return True if *value* fits NUMERIC(precision, scale) without rounding.

    A value fits only when it is finite, has no significant digits beyond
    *scale*, and its integer part does not exceed ``precision - scale`` digits.
    """
    if value.is_nan() or value.is_infinite():
        return False
    quantum = Decimal(1).scaleb(-scale)
    try:
        quantized = value.quantize(quantum)
    except (InvalidOperation, ValueError):
        return False
    if quantized != value:
        return False
    integer_digits = precision - scale
    return quantized == 0 or quantized.adjusted() + 1 <= integer_digits


def _parse_source_row_id(value: Any) -> int:
    """Parse *value* into a positive BIGINT-compatible integer.

    Raises
    ------
    ValueError
        If the value is missing, non-finite, non-integer, or out of the
        positive BIGINT range.
    """
    dec = _to_decimal(value)
    if dec.is_nan() or dec.is_infinite():
        raise ValueError(f"source_row_id is not a finite number: {value!r}")
    if dec != dec.to_integral_value():
        raise ValueError(f"source_row_id is not an integer: {value!r}")
    row_id = int(dec)
    if row_id < 1 or row_id > BIGINT_MAX:
        raise ValueError(f"source_row_id out of positive BIGINT range: {row_id}")
    return row_id


def _parse_quantity(value: Any) -> int:
    """Parse *value* into a BIGINT-compatible integer using Decimal.

    Raises
    ------
    ValueError
        If the value is non-finite, non-integer, or out of the BIGINT range.
    """
    dec = _to_decimal(value)
    if dec.is_nan() or dec.is_infinite():
        raise ValueError(f"quantity is not a finite number: {value!r}")
    if dec != dec.to_integral_value():
        raise ValueError(f"non-integer quantity: {value!r}")
    quantity = int(dec)
    if quantity < BIGINT_MIN or quantity > BIGINT_MAX:
        raise ValueError(f"quantity out of BIGINT range: {quantity}")
    return quantity


def _parse_price(value: Any) -> Decimal:
    """Parse *value* into a NUMERIC(12,4)-compatible Decimal.

    Raises
    ------
    ValueError
        If the value is non-finite or does not fit NUMERIC(12,4).
    """
    dec = _to_decimal(value)
    if dec.is_nan() or dec.is_infinite():
        raise ValueError(f"price is not a finite number: {value!r}")
    if not _fits_numeric(dec, PRICE_PRECISION, PRICE_SCALE):
        raise ValueError(f"price does not fit NUMERIC(12,4): {value!r}")
    return dec


def _parse_timestamp(value: Any) -> tuple[pd.Timestamp | None, str | None]:
    """Parse *value* into a timezone-naive Timestamp.

    Returns
    -------
    (timestamp, rejection_reason)
        ``timestamp`` is set and ``rejection_reason`` is None on success.
        Otherwise ``timestamp`` is None and ``rejection_reason`` is one of
        ``"invalid_timestamp"`` or ``"timestamp_has_timezone"``.
    """
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None, "invalid_timestamp"
    if getattr(ts, "tz", None) is not None:
        return None, "timestamp_has_timezone"
    return ts, None


# ---------------------------------------------------------------------------
# Row-level transformation
# ---------------------------------------------------------------------------


def transform_row(row: pd.Series) -> tuple[dict[str, Any] | None, str | None]:
    """Transform a single input row.

    Parameters
    ----------
    row: pd.Series
        A row from the cleaned DataFrame.

    Returns
    -------
    (record, rejection_reason)
        ``record`` is the transformed dict when successful (``rejection_reason``
        is None); otherwise ``record`` is None and ``rejection_reason`` is set.
    """
    # Trim text fields (preserve nulls)
    invoice = _trim(row["Invoice"])
    stock_code = _trim(row["StockCode"])
    description = _trim(row["Description"])
    customer_id = _trim(row["Customer ID"])
    country = _trim(row["Country"])

    # Validate required fields are present
    field_values = {
        "Invoice": invoice,
        "StockCode": stock_code,
        "Quantity": row["Quantity"],
        "InvoiceDate": row["InvoiceDate"],
        "Price": row["Price"],
        "Country": country,
    }
    for field in REQUIRED_FIELDS:
        if _is_missing(field_values[field]):
            return None, "missing_required_field"

    # Validate source_row_id (positive BIGINT integer)
    try:
        source_row_id = _parse_source_row_id(row["source_row_id"])
    except (ValueError, InvalidOperation):
        return None, "invalid_source_row_id"

    # Parse numeric fields (reject invalid / out-of-range values)
    try:
        quantity = _parse_quantity(row["Quantity"])
    except (ValueError, InvalidOperation):
        return None, "invalid_quantity"

    try:
        price = _parse_price(row["Price"])
    except (ValueError, InvalidOperation):
        return None, "invalid_price"

    # Parse timestamp (reject invalid or timezone-aware values)
    ts, ts_reason = _parse_timestamp(row["InvoiceDate"])
    if ts_reason is not None:
        return None, ts_reason

    # Derived columns
    invoice_date = ts.strftime("%Y-%m-%d")
    invoice_month = ts.strftime("%Y-%m")
    line_total = Decimal(quantity) * price

    if not _fits_numeric(line_total, LINE_TOTAL_PRECISION, LINE_TOTAL_SCALE):
        return None, "line_total_out_of_range"

    record: dict[str, Any] = {
        "source_row_id": source_row_id,
        "invoice": invoice,
        "stock_code": stock_code,
        "description": description,
        "quantity": quantity,
        "invoice_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "price": f"{price:.4f}",
        "customer_id": customer_id,
        "country": country,
        "invoice_date": invoice_date,
        "line_total": f"{line_total:.4f}",
        "invoice_month": invoice_month,
    }
    return record, None


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def read_cleaned_csv(path: Path) -> pd.DataFrame:
    """Read the cleaned CSV without modifying the source file."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def validate_input_columns(df: pd.DataFrame, expected: list[str]) -> None:
    """Ensure the DataFrame contains exactly the expected input columns."""
    missing = [c for c in expected if c not in df.columns]
    extra = [c for c in df.columns if c not in expected]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
    if extra:
        raise ValueError(f"Unexpected extra columns: {extra}")


def validate_source_row_id_unique(df: pd.DataFrame) -> None:
    """Ensure ``source_row_id`` values are unique across the input dataset.

    Uses Decimal-based exact parsing to avoid floating-point precision loss.
    Valid integer IDs are normalised so that representations like ``"001"`` and
    ``"1"`` are treated as the same ID.  Non-integer or missing values are
    ignored here; the row-level ``transform_row`` function will reject them.

    Raises
    ------
    RuntimeError
        If any two rows share the same normalised integer ``source_row_id``.
    """
    seen: set[int] = set()
    dupes: set[int] = set()
    for raw in df["source_row_id"].tolist():
        try:
            dec = _to_decimal(raw)
            if dec.is_nan() or dec.is_infinite():
                continue  # non-numeric — leave to row-level validation
            if dec != dec.to_integral_value():
                continue  # non-integer — leave to row-level validation
            normalised = int(dec)  # drops leading zeros, etc.
        except (ValueError, InvalidOperation):
            continue  # non-numeric — leave to row-level validation
        if normalised in seen:
            dupes.add(normalised)
        else:
            seen.add(normalised)
    if dupes:
        duplicates = sorted(dupes)
        raise RuntimeError(f"Duplicate source_row_id values in input dataset: {duplicates[:10]}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to CSV, creating the parent directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def write_json_report(report: dict[str, Any], path: Path) -> None:
    """Write a JSON report to disk, creating the parent directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def compute_report(
    input_df: pd.DataFrame,
    transformed_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
) -> dict[str, Any]:
    """Build the transformation report dictionary."""
    # Rejection reason counts
    rejection_reasons: dict[str, int] = {}
    if "rejection_reason" in rejected_df.columns and not rejected_df.empty:
        rejection_reasons = {
            reason: int(count)
            for reason, count in rejected_df["rejection_reason"].value_counts().items()
        }

    # Transformed-output statistics
    if not transformed_df.empty:
        qty = pd.to_numeric(transformed_df["quantity"], errors="coerce")
        price = pd.to_numeric(transformed_df["price"], errors="coerce")
        neg_qty_count = int((qty < 0).sum())
        zero_price_count = int((price == 0).sum())
        missing_customer_id_count = int(transformed_df["customer_id"].isna().sum())
        missing_description_count = int(transformed_df["description"].isna().sum())
    else:
        neg_qty_count = 0
        zero_price_count = 0
        missing_customer_id_count = 0
        missing_description_count = 0

    return {
        "input_row_count": len(input_df),
        "transformed_row_count": len(transformed_df),
        "rejected_row_count": len(rejected_df),
        "rejection_reason_counts": rejection_reasons,
        "negative_quantity_count": neg_qty_count,
        "zero_price_count": zero_price_count,
        "missing_customer_id_count": missing_customer_id_count,
        "missing_description_count": missing_description_count,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_transformation() -> None:
    """Execute the full transformation pipeline."""
    # 1. Read cleaned CSV
    try:
        df = read_cleaned_csv(CLEANED_INPUT)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Cleaned CSV not found at {CLEANED_INPUT}. Run cleaner.py first."
        ) from exc

    # 2. Validate input columns and source_row_id uniqueness
    validate_input_columns(df, EXPECTED_INPUT_COLUMNS)
    validate_source_row_id_unique(df)

    # 3. Transform row by row
    transformed_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        record, reason = transform_row(row)
        if reason is not None:
            rejected = row.to_dict()
            rejected["rejection_reason"] = reason
            rejected_records.append(rejected)
        else:
            transformed_records.append(record)  # type: ignore[arg-type]

    transformed_df = pd.DataFrame(transformed_records, columns=TRANSFORMED_COLUMNS)
    rejected_columns = [*EXPECTED_INPUT_COLUMNS, "rejection_reason"]
    rejected_df = pd.DataFrame(rejected_records, columns=rejected_columns)

    # 4. Ensure source_row_id is unique in transformed output
    if not transformed_df.empty and transformed_df["source_row_id"].duplicated().any():
        raise RuntimeError("source_row_id is not unique in transformed output")

    # 5. Verify row conservation
    if len(df) != len(transformed_df) + len(rejected_df):
        raise RuntimeError(
            f"Row conservation failed: input={len(df)}, "
            f"transformed={len(transformed_df)}, rejected={len(rejected_df)}"
        )

    # 6. Write outputs
    write_csv(transformed_df, TRANSFORMED_PATH)
    write_csv(rejected_df, REJECTED_PATH)

    # 7. Write report
    report = compute_report(df, transformed_df, rejected_df)
    write_json_report(report, REPORT_PATH)

    print(f"Transformed output written to {TRANSFORMED_PATH}")
    print(f"Rejected output written to {REJECTED_PATH}")
    print(f"Transformation report written to {REPORT_PATH}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the transformer pipeline."""
    run_transformation()


if __name__ == "__main__":
    main()
