"""Profiler for the Online Retail II dataset.

Reads the raw CSV, validates column structure, computes quality statistics,
and writes a JSON profile to ``pipeline/data/profiles/``.

Does not modify the raw CSV or implement any cleaning/loading logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# ---------------------------------------------------------------------------
# Paths (relative to the repository root)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # .../fde-ai-sprint

RAW_CSV = REPO_ROOT / "pipeline" / "data" / "raw" / "online_retail_II.csv"

PROFILE_DIR = REPO_ROOT / "pipeline" / "data" / "profiles"
PROFILE_PATH = PROFILE_DIR / "online_retail_II_profile.json"

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
    """Read the raw Online Retail II CSV.

    Parameters
    ----------
    path: Path
        Path to ``online_retail_II.csv``.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the raw data. The original CSV is never modified.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    return df


def validate_columns(df: pd.DataFrame, expected: List[str]) -> None:
    """Ensure the DataFrame contains exactly the expected columns.

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


def compute_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute the full profiling statistics for the DataFrame.

    Parameters
    ----------
    df: pd.DataFrame
        Input DataFrame (already validated).

    Returns
    -------
    Dict[str, Any]
        Dictionary with all profiling results.
    """
    total_rows = len(df)
    total_cols = len(df.columns)

    # Missing-value counts and percentages
    missing_counts = df.isna().sum()
    missing_pct = (missing_counts / total_rows * 100).round(2)

    missing_info: Dict[str, Dict[str, int | float]] = {}
    for col in df.columns:
        missing_info[col] = {
            "count": int(missing_counts[col]),
            "percentage": float(missing_pct[col]),
        }

    # Exact duplicate excess rows and groups
    # An "excess duplicate" is a row beyond the first occurrence where all
    # 8 original CSV columns are identical.
    duplicate_mask = df.duplicated(keep="first")
    excess_duplicate_rows = int(duplicate_mask.sum())
    duplicate_groups = int(
        df.groupby(df.columns.tolist(), dropna=False)
        .size()
        .gt(1)
        .sum()
    )

    # Unique counts per column
    unique_counts: Dict[str, int] = {col: int(df[col].nunique()) for col in df.columns}

    # InvoiceDate min / max
    # InvoiceDate may contain a timestamp; parse it safely.
    invoice_date_col = df["InvoiceDate"]
    try:
        parsed_dates = pd.to_datetime(invoice_date_col, errors="coerce")
        min_date = parsed_dates.min()
        max_date = parsed_dates.max()
        min_date_str = str(min_date) if not pd.isna(min_date) else "NaT"
        max_date_str = str(max_date) if not pd.isna(max_date) else "NaT"
    except Exception:
        min_date_str = "parse_error"
        max_date_str = "parse_error"

    # Quantity breakdown: negative / zero / positive
    qty_col = pd.to_numeric(df["Quantity"], errors="coerce")
    neg_qty = int((qty_col < 0).sum())
    zero_qty = int((qty_col == 0).sum())
    pos_qty = int((qty_col > 0).sum())

    # Price breakdown: negative / zero / positive
    price_col = pd.to_numeric(df["Price"], errors="coerce")
    neg_price = int((price_col < 0).sum())
    zero_price = int((price_col == 0).sum())
    pos_price = int((price_col > 0).sum())

    # Invoice prefix counts
    # Prefixes are the leading character(s) of the Invoice field.
    # We normalise to string and take the first character if present.
    invoice_col = df["Invoice"].astype(str)
    prefix_counts: Dict[str, int] = {}
    for prefix in ("5", "4", "C", "A"):
        count = int((invoice_col.str.startswith(prefix)).sum())
        prefix_counts[prefix] = count

    profile: Dict[str, Any] = {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "missing_values": missing_info,
        "excess_duplicate_rows": excess_duplicate_rows,
        "duplicate_groups": duplicate_groups,
        "unique_counts": unique_counts,
        "invoice_date_range": {
            "min": min_date_str,
            "max": max_date_str,
        },
        "quantity_breakdown": {
            "negative": neg_qty,
            "zero": zero_qty,
            "positive": pos_qty,
        },
        "price_breakdown": {
            "negative": neg_price,
            "zero": zero_price,
            "positive": pos_price,
        },
        "invoice_prefix_counts": prefix_counts,
    }

    return profile


def save_profile(profile: Dict[str, Any], path: Path) -> None:
    """Write the profiling JSON to disk.

    Parameters
    ----------
    profile: Dict[str, Any]
        Profile dictionary as returned by :func:`compute_profile`.
    path: Path
        Target JSON file path. Directory will be created if it does not exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the profiler and write the profile JSON."""
    # 1. Read raw CSV (no modification)
    df = read_raw_csv(RAW_CSV)

    # 2. Validate column structure
    validate_columns(df, EXPECTED_COLUMNS)

    # 3. Compute profile
    profile = compute_profile(df)

    # 4. Save profile JSON
    save_profile(profile, PROFILE_PATH)

    print(f"Profile written to {PROFILE_PATH}")


if __name__ == "__main__":
    main()