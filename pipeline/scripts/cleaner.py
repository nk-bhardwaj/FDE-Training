"""Cleaner for the Online Retail II dataset.

Reads the raw CSV, applies documented cleaning rules, and writes cleaned and
quarantined outputs along with a JSON cleaning report.

Does not modify the raw CSV or implement target-schema conversions (belong in
transformer.py).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Repository root and paths (relative to __file__, not cwd)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # .../fde-ai-sprint

RAW_CSV = REPO_ROOT / "pipeline" / "data" / "raw" / "online_retail_II.csv"

CLEANED_DIR = REPO_ROOT / "pipeline" / "data" / "cleaned"
CLEANED_PATH = CLEANED_DIR / "online_retail_II_cleaned.csv"

QUARANTINED_DIR = REPO_ROOT / "pipeline" / "data" / "quarantined"
QUARANTINED_PATH = QUARANTINED_DIR / "online_retail_II_quarantined.csv"
DUPLICATES_PATH = QUARANTINED_DIR / "online_retail_II_duplicates.csv"

PROFILE_DIR = REPO_ROOT / "pipeline" / "data" / "profiles"
CLEANING_REPORT_PATH = PROFILE_DIR / "online_retail_II_cleaning_report.json"

EXPECTED_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def read_raw_csv(path: Path) -> pd.DataFrame:
    """Read the raw Online Retail II CSV without modifying the source file.

    Parameters
    ----------
    path: Path
        Path to ``online_retail_II.csv``.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the raw data.
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def validate_columns(df: pd.DataFrame, expected: list[str]) -> None:
    """Ensure the DataFrame contains exactly the expected eight columns.

    Parameters
    ----------
    df: pd.DataFrame
        Input DataFrame.
    expected: List[str]
        List of column names that must be present.

    Raises
    ------
    ValueError
        If any expected column is missing or there are unexpected columns.
    """
    missing = [c for c in expected if c not in df.columns]
    extra = [c for c in df.columns if c not in expected]

    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    if extra:
        raise ValueError(f"Unexpected extra columns: {extra}")


def assign_source_row_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Add a stable ``source_row_id`` column starting at 1 after the header.

    The ID is based on the original CSV row order and is preserved across all
    downstream stages (cleaning, transformation, validation, rejection).

    Parameters
    ----------
    df: pd.DataFrame
        Input DataFrame.

    Returns
    -------
    pd.DataFrame
        DataFrame with an added ``source_row_id`` column.
    """
    df = df.copy()
    df["source_row_id"] = range(1, len(df) + 1)
    return df


def quarantine_negative_price(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split *df* into cleaned and quarantined frames based on negative Price.

    Records where ``Price < 0`` are sent to quarantine with a
    ``rejection_reason = 'negative_price'``. All other records become cleaned.

    Parameters
    ----------
    df: pd.DataFrame
        Input DataFrame (must already have ``source_row_id``).

    Returns
    -------
    cleaned: pd.DataFrame
        Rows with ``Price >= 0``.
    quarantined: pd.DataFrame
        Rows with ``Price < 0``, augmented with ``rejection_reason``.
    """
    price_col = pd.to_numeric(df["Price"], errors="coerce")
    neg_mask = price_col < 0

    cleaned = df[~neg_mask].copy()
    quarantined = df[neg_mask].copy()
    quarantined["rejection_reason"] = "negative_price"

    return cleaned, quarantined


def deduplicate_exact(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split *df* into unique and duplicate frames based on the 8 source columns.

    Exact duplicates are detected using all 8 original source columns
    (``EXPECTED_COLUMNS``), excluding the generated ``source_row_id``.
    The first occurrence of each exact record is kept; subsequent occurrences
    are moved to the duplicates frame. Both frames preserve ``source_row_id``.

    Parameters
    ----------
    df: pd.DataFrame
        Input DataFrame (must already have ``source_row_id``).

    Returns
    -------
    unique: pd.DataFrame
        First occurrence of each unique combination of source columns.
    duplicates: pd.DataFrame
        Subsequent exact duplicate occurrences.
    """
    # Detect exact duplicates on the 8 original source columns (no source_row_id)
    dup_mask = df.duplicated(subset=EXPECTED_COLUMNS, keep="first")

    unique = df[~dup_mask].copy()
    duplicates = df[dup_mask].copy()

    return unique, duplicates


def compute_cleaning_report(
    input_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    quarantined_df: pd.DataFrame,
    duplicates_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Generate the JSON cleaning report.

    Parameters
    ----------
    input_df: pd.DataFrame
        Original input DataFrame.
    cleaned_df: pd.DataFrame
        Output DataFrame after applying cleaning rules (final cleaned rows).
    quarantined_df: pd.DataFrame
        Output DataFrame after quarantine step (negative-price rows).
    duplicates_df: pd.DataFrame | None
        DataFrame of exact duplicate rows removed during deduplication.

    Returns
    -------
    Dict[str, Any]
        Dictionary ready to be written as JSON.
    """
    total_input = len(input_df)
    total_cleaned = len(cleaned_df)
    total_quarantined = len(quarantined_df)
    total_duplicates = len(duplicates_df) if duplicates_df is not None else 0
    total_unique_after_dedup = total_cleaned + total_quarantined

    # Verify row conservation: input = cleaned + negative_price_quarantined + duplicates
    if total_input != total_cleaned + total_quarantined + total_duplicates:
        raise RuntimeError(
            f"Row conservation failed: input={total_input}, "
            f"cleaned={total_cleaned}, "
            f"quarantined={total_quarantined}, "
            f"duplicates={total_duplicates}"
        )

    # Quarantine reason counts
    quarantine_reasons: dict[str, int] = {}
    if "rejection_reason" in quarantined_df.columns:
        quarantine_reasons = {
            reason: int(count)
            for reason, count in quarantined_df["rejection_reason"].value_counts().items()
        }

    # Cleaned-output statistics
    price_col = pd.to_numeric(cleaned_df["Price"], errors="coerce")
    qty_col = pd.to_numeric(cleaned_df["Quantity"], errors="coerce")

    neg_qty_count = int((qty_col < 0).sum()) if not qty_col.empty else 0
    zero_price_count = int((price_col == 0).sum()) if not price_col.empty else 0
    missing_customer_id_count = int(cleaned_df["Customer ID"].isna().sum())
    missing_description_count = int(cleaned_df["Description"].isna().sum())

    # Exact duplicate excess count using only the original dataset columns
    excess_duplicate_rows = int(input_df.duplicated(subset=EXPECTED_COLUMNS, keep="first").sum())

    report: dict[str, Any] = {
        "input_row_count": total_input,
        "cleaned_row_count": total_cleaned,
        "final_cleaned_row_count": total_cleaned,
        "quarantined_row_count": total_quarantined,
        "negative_price_quarantined_count": total_quarantined,
        "duplicate_rows_removed": total_duplicates,
        "unique_rows_after_dedup": total_unique_after_dedup,
        "quarantine_reason_counts": quarantine_reasons,
        "duplicate_excess_rows_in_input": excess_duplicate_rows,
        "negative_quantity_count_cleaned": neg_qty_count,
        "zero_price_count_cleaned": zero_price_count,
        "missing_customer_id_count_cleaned": missing_customer_id_count,
        "missing_description_count_cleaned": missing_description_count,
    }

    return report


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to CSV, creating the parent directory if needed.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame to write.
    path: Path
        Target CSV path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def write_json_report(report: dict[str, Any], path: Path) -> None:
    """Write a JSON report to disk, creating the parent directory if needed.

    Parameters
    ----------
    report: Dict[str, Any]
        Report dictionary.
    path: Path
        Target JSON path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def run_cleaning() -> None:
    """Execute the full cleaning pipeline.

    1. Read raw CSV (no modification).
    2. Validate column structure.
    3. Assign stable ``source_row_id``.
    4. Quarantine negative-price records first.
    5. Deduplicate exact records among the remaining non-negative-price records.
    6. Write cleaned, quarantined, duplicates, and the JSON report.

    No target-schema conversions are performed here; that is left to
    ``transformer.py``.
    """
    # 1. Read raw CSV
    try:
        df = read_raw_csv(RAW_CSV)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Raw CSV not found at {RAW_CSV}. Place the file and re-run the cleaner."
        ) from exc

    # 2. Validate column structure
    validate_columns(df, EXPECTED_COLUMNS)

    # 3. Assign stable source_row_id
    df = assign_source_row_ids(df)

    # 4. Quarantine negative-price records first
    cleaned_pre_dedup, quarantined = quarantine_negative_price(df)

    # 5. Deduplicate exact records among the remaining non-negative-price records
    cleaned, duplicates = deduplicate_exact(cleaned_pre_dedup)

    # 6. Write outputs
    write_csv(cleaned, CLEANED_PATH)
    write_csv(quarantined, QUARANTINED_PATH)
    write_csv(duplicates, DUPLICATES_PATH)

    # 6b. Generate and write cleaning report
    report = compute_cleaning_report(df, cleaned, quarantined, duplicates)
    write_json_report(report, CLEANING_REPORT_PATH)

    print(f"Cleaned output written to {CLEANED_PATH}")
    print(f"Quarantined output written to {QUARANTINED_PATH}")
    print(f"Duplicates audit written to {DUPLICATES_PATH}")
    print(f"Cleaning report written to {CLEANING_REPORT_PATH}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the cleaner pipeline."""
    run_cleaning()


if __name__ == "__main__":
    main()
