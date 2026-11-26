"""Independent data-quality validation for the transformed Online Retail II data.

Validates the 12-column warehouse-shaped output described in
``pipeline/docs/schema-design.md`` without importing or reusing transformation
logic. The module reads the transformed CSV, applies schema, record, and
derived-column checks, and writes a JSON report under ``pipeline/data/profiles/``.

Design notes
------------
* Structural and string checks use vectorised pandas masks.
* Monetary and integer domain checks use :class:`decimal.Decimal` through
  ``Series.map`` so values are compared exactly instead of through binary
  floating point.
* Business-rule-preserved values (negative quantity, zero price, missing
  description/customer ID) are counted for reporting but never treated as
  failures.
* No database, LLM, or transformation calls are made.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Paths (relative to __file__, not cwd)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # .../fde-ai-sprint

TRANSFORMED_INPUT = REPO_ROOT / "pipeline" / "data" / "cleaned" / "online_retail_II_transformed.csv"

QUALITY_REPORT_PATH = (
    REPO_ROOT / "pipeline" / "data" / "profiles" / "online_retail_II_quality_report.json"
)

# ---------------------------------------------------------------------------
# Schema contract (schema-design.md Section 2 and Section 4)
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = [
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

REQUIRED_COLUMNS = [
    "source_row_id",
    "invoice",
    "stock_code",
    "quantity",
    "invoice_timestamp",
    "price",
    "country",
    "invoice_date",
    "line_total",
    "invoice_month",
]

NULLABLE_COLUMNS = ["description", "customer_id"]

# ---------------------------------------------------------------------------
# Numeric domain constants (mirror the PostgreSQL target schema)
# ---------------------------------------------------------------------------

BIGINT_MIN = -(2**63)
BIGINT_MAX = 2**63 - 1

PRICE_PRECISION = 12
PRICE_SCALE = 4

LINE_TOTAL_PRECISION = 14
LINE_TOTAL_SCALE = 4

MAX_SAMPLES = 5

# ISO-like timezone suffixes: ``Z``, ``+HH:MM``, ``-HHMM``, etc.
_TIMEZONE_SUFFIX = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$")

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one validation rule."""

    rule_id: str
    category: str
    column: str | None
    description: str
    failure_count: int
    sample_failures: tuple[str, ...] = ()
    details: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        """Return True when the rule found no failures."""
        return self.failure_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of this check."""
        result: dict[str, Any] = {
            "rule_id": self.rule_id,
            "category": self.category,
            "column": self.column,
            "description": self.description,
            "status": "passed" if self.passed else "failed",
            "failure_count": self.failure_count,
            "sample_failures": list(self.sample_failures),
        }
        if self.details is not None:
            result["details"] = self.details
        return result


# ---------------------------------------------------------------------------
# Low-level parsing helpers
# ---------------------------------------------------------------------------


def _is_missing(value: Any) -> bool:
    """Return True for None, NaN/NA, or a blank/whitespace string."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _parse_decimal(value: Any) -> Decimal | None:
    """Parse *value* into a finite Decimal, or return None when invalid."""
    if _is_missing(value):
        return None
    try:
        dec = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if dec.is_nan() or dec.is_infinite():
        return None
    return dec


def _parse_bigint(value: Any) -> int | None:
    """Parse *value* into a BIGINT integer, allowing negative values."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    if re.fullmatch(r"[+-]?\d+", text) is None:
        return None
    try:
        number = int(text)
    except ValueError:
        return None
    if number < BIGINT_MIN or number > BIGINT_MAX:
        return None
    return number


def _parse_positive_bigint(value: Any) -> int | None:
    """Parse *value* into a positive BIGINT integer."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d+", text) is None:
        return None
    number = int(text)
    if number < 1 or number > BIGINT_MAX:
        return None
    return number


def _fits_numeric(value: Decimal, precision: int, scale: int) -> bool:
    """Return True if *value* fits NUMERIC(precision, scale) without rounding."""
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


def _blank_mask(series: pd.Series) -> pd.Series:
    """Return a boolean mask for null, NA, empty, or whitespace-only values."""
    text = series.astype("string").str.strip()
    return text.isna() | text.eq("").fillna(False)


def _parse_timestamp_scalar(value: Any, *, utc: bool = False) -> pd.Timestamp:
    """Parse a single timestamp value, returning NaT on failure."""
    if _is_missing(value):
        return pd.NaT
    try:
        return pd.to_datetime(value, errors="coerce", utc=utc)
    except (TypeError, ValueError):
        return pd.NaT


def _safe_to_datetime(
    series: pd.Series,
    *,
    utc: bool = False,
    format: str | None = None,
) -> pd.Series:
    """Parse a timestamp Series, falling back to scalar parsing on errors."""
    try:
        return pd.to_datetime(series, errors="coerce", utc=utc, format=format)
    except (TypeError, ValueError):
        return series.map(lambda value: _parse_timestamp_scalar(value, utc=utc))


def _timestamp_strftime(parsed: pd.Series, fmt: str) -> pd.Series:
    """Format a parsed timestamp Series, handling datetime and object dtypes."""
    if pd.api.types.is_datetime64_any_dtype(parsed):
        return parsed.dt.strftime(fmt)
    return parsed.map(lambda value: value.strftime(fmt) if pd.notna(value) else None)


def _timezone_naive_mask(parsed: pd.Series) -> pd.Series:
    """Return True for values that are timezone-naive timestamps."""
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return pd.Series(False, index=parsed.index)
    if pd.api.types.is_datetime64_any_dtype(parsed):
        return pd.Series(True, index=parsed.index)
    return parsed.map(lambda value: pd.notna(value) and getattr(value, "tz", None) is None)


def _sample_source_row_ids(df: pd.DataFrame, mask: pd.Series) -> tuple[str, ...]:
    """Return up to ``MAX_SAMPLES`` source_row_id values from failing rows."""
    if "source_row_id" not in df.columns or mask.empty:
        return ()
    return tuple(str(value) for value in df.loc[mask, "source_row_id"].head(MAX_SAMPLES))


def _result(
    rule_id: str,
    category: str,
    column: str | None,
    description: str,
    mask: pd.Series,
    df: pd.DataFrame,
    *,
    samples: list[Any] | tuple[Any, ...] | None = None,
    details: dict[str, Any] | None = None,
) -> CheckResult:
    """Build a CheckResult from a failure mask."""
    sample_values = _sample_source_row_ids(df, mask) if samples is None else samples
    return CheckResult(
        rule_id=rule_id,
        category=category,
        column=column,
        description=description,
        failure_count=int(mask.sum()),
        sample_failures=tuple(str(value) for value in sample_values),
        details=details,
    )


# ---------------------------------------------------------------------------
# Parsed column cache (avoids re-parsing Decimal / timestamp columns)
# ---------------------------------------------------------------------------


def _parse_columns(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Parse the columns needed by record and derived-column checks."""
    timestamp_text = df["invoice_timestamp"].astype("string").str.strip()
    timestamp_blank = timestamp_text.isna() | timestamp_text.eq("").fillna(False)
    timezone_aware = timestamp_text.str.contains(_TIMEZONE_SUFFIX, regex=True).fillna(False)

    naive_text = timestamp_text.where(~timezone_aware & ~timestamp_blank)
    aware_text = timestamp_text.where(timezone_aware)

    parsed_naive = _safe_to_datetime(naive_text, format="mixed")
    parsed_aware = _safe_to_datetime(aware_text, utc=True)

    timestamp_naive = parsed_naive.notna() & _timezone_naive_mask(parsed_naive)
    timestamp_valid = parsed_naive.notna() | parsed_aware.notna()
    timestamp_timezone_aware = (timezone_aware & parsed_aware.notna()) | (
        parsed_naive.notna() & ~timestamp_naive
    )

    return {
        "source_row_id": df["source_row_id"].map(_parse_positive_bigint),
        "quantity": df["quantity"].map(_parse_bigint),
        "price": df["price"].map(_parse_decimal),
        "line_total": df["line_total"].map(_parse_decimal),
        "timestamp": parsed_naive.where(timestamp_naive),
        "timestamp_valid": timestamp_valid,
        "timestamp_naive": timestamp_naive,
        "timestamp_timezone_aware": timestamp_timezone_aware,
    }


# ---------------------------------------------------------------------------
# Schema checks
# ---------------------------------------------------------------------------


def validate_schema(df: pd.DataFrame) -> list[CheckResult]:
    """Validate column set, order, required columns, and nullable columns."""
    actual_columns = list(df.columns)
    missing = [column for column in EXPECTED_COLUMNS if column not in actual_columns]
    extra = [column for column in actual_columns if column not in EXPECTED_COLUMNS]

    checks: list[CheckResult] = [
        CheckResult(
            rule_id="DQ-SCHEMA-01",
            category="schema",
            column=None,
            description="DataFrame contains exactly the 12 expected transformed columns",
            failure_count=len(missing) + len(extra),
            sample_failures=tuple(missing + extra),
            details={"missing_columns": missing, "extra_columns": extra},
        )
    ]

    order_matches = actual_columns == EXPECTED_COLUMNS
    checks.append(
        CheckResult(
            rule_id="DQ-SCHEMA-02",
            category="schema",
            column=None,
            description="Column order matches the expected transformed schema",
            failure_count=0 if order_matches else 1,
            sample_failures=() if order_matches else ("column_order_mismatch",),
            details={"expected_order": EXPECTED_COLUMNS, "actual_order": actual_columns},
        )
    )

    required_counts: dict[str, int] = {}
    required_mask = pd.Series(False, index=df.index)
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            continue
        column_mask = _blank_mask(df[column])
        required_counts[column] = int(column_mask.sum())
        required_mask |= column_mask

    checks.append(
        _result(
            rule_id="DQ-SCHEMA-03",
            category="schema",
            column=None,
            description="Required columns must not be null or blank",
            mask=required_mask,
            df=df,
            details={"column_failure_counts": required_counts},
        )
    )

    nullable_missing = [column for column in NULLABLE_COLUMNS if column not in df.columns]
    nullable_overlap = sorted(set(NULLABLE_COLUMNS) & set(REQUIRED_COLUMNS))
    nullable_counts = {
        column: int(_blank_mask(df[column]).sum())
        for column in NULLABLE_COLUMNS
        if column in df.columns
    }
    nullable_contract_ok = not nullable_missing and not nullable_overlap

    checks.append(
        CheckResult(
            rule_id="DQ-SCHEMA-04",
            category="schema",
            column=None,
            description=("Nullable columns (description, customer_id) may contain nulls"),
            failure_count=0 if nullable_contract_ok else 1,
            sample_failures=tuple(nullable_missing + nullable_overlap),
            details={
                "nullable_columns": NULLABLE_COLUMNS,
                "null_counts": nullable_counts,
            },
        )
    )

    return checks


# ---------------------------------------------------------------------------
# Record checks
# ---------------------------------------------------------------------------


def _record_checks(
    df: pd.DataFrame,
    parsed: dict[str, pd.Series],
) -> tuple[list[CheckResult], pd.Series]:
    """Validate row-level record domains and return the combined failure mask."""
    checks: list[CheckResult] = []

    source_row_id = parsed["source_row_id"]
    source_row_id_invalid = source_row_id.isna()
    checks.append(
        _result(
            rule_id="DQ-REC-01",
            category="record",
            column="source_row_id",
            description="source_row_id must be a positive integer",
            mask=source_row_id_invalid,
            df=df,
        )
    )

    valid_ids = source_row_id.dropna()
    duplicate_ids = valid_ids[valid_ids.duplicated(keep=False)]
    duplicate_mask = pd.Series(False, index=df.index)
    if not duplicate_ids.empty:
        duplicate_mask.loc[duplicate_ids.index] = True
    checks.append(
        _result(
            rule_id="DQ-REC-02",
            category="record",
            column="source_row_id",
            description="source_row_id must be unique across the dataset",
            mask=duplicate_mask,
            df=df,
            samples=duplicate_ids.drop_duplicates().head(MAX_SAMPLES).tolist(),
        )
    )

    for rule_id, column in (
        ("DQ-REC-03", "invoice"),
        ("DQ-REC-04", "stock_code"),
        ("DQ-REC-05", "country"),
    ):
        mask = _blank_mask(df[column])
        checks.append(
            _result(
                rule_id=rule_id,
                category="record",
                column=column,
                description=f"{column} must not be blank",
                mask=mask,
                df=df,
            )
        )

    quantity = parsed["quantity"]
    checks.append(
        _result(
            rule_id="DQ-REC-06",
            category="record",
            column="quantity",
            description="quantity must be an integer (negative values allowed)",
            mask=quantity.isna(),
            df=df,
        )
    )

    price = parsed["price"]
    price_invalid = price.isna() | price.map(lambda value: value is not None and value < 0)
    checks.append(
        _result(
            rule_id="DQ-REC-07",
            category="record",
            column="price",
            description=("price must be a finite, non-negative decimal (zero allowed)"),
            mask=price_invalid,
            df=df,
        )
    )

    price_out_of_range = price.map(
        lambda value: value is None or not _fits_numeric(value, PRICE_PRECISION, PRICE_SCALE)
    )
    checks.append(
        _result(
            rule_id="DQ-REC-08",
            category="record",
            column="price",
            description="price must fit NUMERIC(12,4)",
            mask=price_out_of_range,
            df=df,
        )
    )

    timestamp_valid = parsed["timestamp_valid"]
    checks.append(
        _result(
            rule_id="DQ-REC-09",
            category="record",
            column="invoice_timestamp",
            description="invoice_timestamp must be a valid timestamp",
            mask=~timestamp_valid,
            df=df,
        )
    )

    timestamp_timezone_aware = parsed["timestamp_timezone_aware"]
    checks.append(
        _result(
            rule_id="DQ-REC-10",
            category="record",
            column="invoice_timestamp",
            description="invoice_timestamp must be timezone-naive",
            mask=timestamp_timezone_aware,
            df=df,
        )
    )

    combined = (
        source_row_id_invalid
        | duplicate_mask
        | _blank_mask(df["invoice"])
        | _blank_mask(df["stock_code"])
        | _blank_mask(df["country"])
        | quantity.isna()
        | price_invalid
        | price_out_of_range
        | ~timestamp_valid
        | timestamp_timezone_aware
    )
    return checks, combined


# ---------------------------------------------------------------------------
# Derived-column checks
# ---------------------------------------------------------------------------


def _derived_checks(
    df: pd.DataFrame,
    parsed: dict[str, pd.Series],
) -> tuple[list[CheckResult], pd.Series]:
    """Validate derived columns and return the combined failure mask."""
    checks: list[CheckResult] = []

    expected_date = _timestamp_strftime(parsed["timestamp"], "%Y-%m-%d")
    actual_date = df["invoice_date"].astype("string").str.strip()
    date_mismatch = (actual_date != expected_date).fillna(True)
    date_mask = expected_date.isna() | actual_date.isna() | date_mismatch
    checks.append(
        _result(
            rule_id="DQ-DER-01",
            category="derived",
            column="invoice_date",
            description="invoice_date must equal the date portion of invoice_timestamp",
            mask=date_mask,
            df=df,
        )
    )

    expected_month = _timestamp_strftime(parsed["timestamp"], "%Y-%m")
    actual_month = df["invoice_month"].astype("string").str.strip()
    month_mismatch = (actual_month != expected_month).fillna(True)
    month_mask = expected_month.isna() | actual_month.isna() | month_mismatch
    checks.append(
        _result(
            rule_id="DQ-DER-02",
            category="derived",
            column="invoice_month",
            description="invoice_month must match YYYY-MM from invoice_timestamp",
            mask=month_mask,
            df=df,
        )
    )

    quantity = parsed["quantity"]
    price = parsed["price"]
    line_total = parsed["line_total"]
    expected_line_total = pd.Series(
        [
            Decimal(quantity_value) * price_value
            if quantity_value is not None and price_value is not None
            else None
            for quantity_value, price_value in zip(quantity, price, strict=True)
        ],
        index=df.index,
    )
    line_total_mismatch = (line_total != expected_line_total).fillna(True)
    line_total_mask = expected_line_total.isna() | line_total.isna() | line_total_mismatch
    checks.append(
        _result(
            rule_id="DQ-DER-03",
            category="derived",
            column="line_total",
            description="line_total must equal quantity multiplied by price",
            mask=line_total_mask,
            df=df,
        )
    )

    line_total_out_of_range = line_total.map(
        lambda value: (
            value is None or not _fits_numeric(value, LINE_TOTAL_PRECISION, LINE_TOTAL_SCALE)
        )
    )
    checks.append(
        _result(
            rule_id="DQ-DER-04",
            category="derived",
            column="line_total",
            description="line_total must fit NUMERIC(14,4)",
            mask=line_total_out_of_range,
            df=df,
        )
    )

    combined = date_mask | month_mask | line_total_mask | line_total_out_of_range
    return checks, combined


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def _business_rule_counts(df: pd.DataFrame) -> dict[str, int]:
    """Count business-rule-preserved values without treating them as failures."""
    quantity = (
        pd.to_numeric(df["quantity"], errors="coerce")
        if "quantity" in df.columns
        else pd.Series(dtype="float64")
    )
    price = (
        pd.to_numeric(df["price"], errors="coerce")
        if "price" in df.columns
        else pd.Series(dtype="float64")
    )
    return {
        "negative_quantity_rows": int((quantity < 0).sum()),
        "zero_price_rows": int((price == 0).sum()),
        "missing_description_rows": int(_blank_mask(df["description"]).sum())
        if "description" in df.columns
        else 0,
        "missing_customer_id_rows": int(_blank_mask(df["customer_id"]).sum())
        if "customer_id" in df.columns
        else 0,
    }


def _nullable_null_counts(df: pd.DataFrame) -> dict[str, int]:
    """Return null/blank counts for nullable columns that are present."""
    return {
        column: int(_blank_mask(df[column]).sum())
        for column in NULLABLE_COLUMNS
        if column in df.columns
    }


def build_report(
    df: pd.DataFrame,
    checks: list[CheckResult],
    failure_mask: pd.Series,
    *,
    input_path: Path | str | None = None,
) -> dict[str, Any]:
    """Assemble the JSON-serialisable quality report."""
    failed_checks = [check for check in checks if not check.passed]

    failure_counts = {
        check.rule_id: check.failure_count for check in checks if check.failure_count > 0
    }

    column_failure_counts: dict[str, int] = {}
    for check in checks:
        if check.column is not None and check.failure_count > 0:
            column_failure_counts[check.column] = (
                column_failure_counts.get(check.column, 0) + check.failure_count
            )
        if check.details is not None:
            for column, count in check.details.get("column_failure_counts", {}).items():
                if count > 0:
                    column_failure_counts[column] = column_failure_counts.get(column, 0) + count

    return {
        "report_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "input_path": str(input_path) if input_path is not None else None,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "expected_columns": EXPECTED_COLUMNS,
        "status": "failed" if failed_checks else "passed",
        "summary": {
            "total_checks": len(checks),
            "passed_checks": len(checks) - len(failed_checks),
            "failed_checks": len(failed_checks),
            "total_failure_count": sum(check.failure_count for check in checks),
            "rows_with_any_failure": int(failure_mask.sum()),
        },
        "failure_counts": failure_counts,
        "column_failure_counts": column_failure_counts,
        "checks": [check.to_dict() for check in checks],
        "nullable_column_null_counts": _nullable_null_counts(df),
        "business_rule_counts": _business_rule_counts(df),
        "notes": [
            "Failure counts are per check; one row may fail multiple checks.",
            "Negative quantity, zero price, missing description, and missing "
            "customer_id are permitted and reported separately, not as failures.",
        ],
    }


# ---------------------------------------------------------------------------
# Public validation entry points
# ---------------------------------------------------------------------------


def validate_records(
    df: pd.DataFrame,
) -> tuple[list[CheckResult], pd.Series]:
    """Validate record-level rules. Returns checks and the combined mask."""
    parsed = _parse_columns(df)
    return _record_checks(df, parsed)


def validate_derived_columns(
    df: pd.DataFrame,
) -> tuple[list[CheckResult], pd.Series]:
    """Validate derived-column rules. Returns checks and the combined mask."""
    parsed = _parse_columns(df)
    return _derived_checks(df, parsed)


def validate_dataframe(
    df: pd.DataFrame,
    *,
    input_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run all quality checks against *df* and return the report dictionary.

    If expected columns are missing, schema checks are reported and row-level
    checks are skipped because their required inputs are unavailable.
    """
    schema_checks = validate_schema(df)
    missing = [column for column in EXPECTED_COLUMNS if column not in df.columns]

    if missing:
        report = build_report(
            df,
            schema_checks,
            pd.Series(False, index=df.index),
            input_path=input_path,
        )
        report["record_checks_skipped"] = True
        report["skip_reason"] = f"Missing expected columns: {missing}"
        return report

    parsed = _parse_columns(df)
    record_checks, record_mask = _record_checks(df, parsed)
    derived_checks, derived_mask = _derived_checks(df, parsed)
    combined_mask = record_mask | derived_mask

    return build_report(
        df,
        schema_checks + record_checks + derived_checks,
        combined_mask,
        input_path=input_path,
    )


# ---------------------------------------------------------------------------
# I/O and orchestration
# ---------------------------------------------------------------------------


def read_transformed_csv(path: Path) -> pd.DataFrame:
    """Read the transformed CSV as strings without modifying the source file."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def write_json_report(report: dict[str, Any], path: Path) -> None:
    """Write the quality report to disk, creating the parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)


def run_validation(
    input_path: Path | str | None = None,
    report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read, validate, and write the quality report. Returns the report."""
    resolved_input = Path(input_path) if input_path is not None else TRANSFORMED_INPUT
    resolved_report = Path(report_path) if report_path is not None else QUALITY_REPORT_PATH

    df = read_transformed_csv(resolved_input)
    report = validate_dataframe(df, input_path=resolved_input)
    write_json_report(report, resolved_report)
    summary = report["summary"]
    print(f"Quality report written to {resolved_report}")
    print(
        f"Status: {report['status']} | rows={report['total_rows']} | "
        f"checks={summary['total_checks']} | "
        f"failed_checks={summary['failed_checks']} | "
        f"rows_with_any_failure={summary['rows_with_any_failure']}"
    )
    return report


def main() -> None:
    """Run the full validation and exit non-zero when the report fails."""
    report = run_validation()
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
