"""Unit tests for pipeline/scripts/cleaner.py.

All tests use small in-memory pandas DataFrames and directly import
cleaner functions. No actual dataset rows are read.

Important: to import ``cleaner`` the test directory adds
``pipeline/scripts`` to :data:`sys.path` so that the module can be
loaded as a top-level module regardless of the working directory.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Ensure cleaner.py is importable from pipeline/scripts regardless of cwd
# ---------------------------------------------------------------------------
_cleaner_src = Path(__file__).resolve().parent.parent / "scripts"
if str(_cleaner_src) not in sys.path:
    sys.path.insert(0, str(_cleaner_src))

import cleaner  # noqa: E402
from cleaner import (  # noqa: E402
    assign_source_row_ids,
    deduplicate_exact,
    quarantine_negative_price,
    validate_columns,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_row(**overrides) -> pd.Series:
    """Return a minimal valid input row Series with all EXPECTED_COLUMNS."""
    default = {
        "Invoice": "INV-1",
        "StockCode": "SKU-1",
        "Description": "Product 1",
        "Quantity": "2",
        "InvoiceDate": "2009-12-01 07:45:00",
        "Price": "6.95",
        "Customer ID": "13085",
        "Country": "United Kingdom",
    }
    default.update(overrides)
    return pd.Series(default, dtype=str)


def _make_df(*rows: dict) -> pd.DataFrame:
    """Build a DataFrame from row dicts and assign source_row_id."""
    df = pd.DataFrame(list(rows), dtype=str)
    return assign_source_row_ids(df)


def _make_duplicate_df() -> pd.DataFrame:
    """Create a DataFrame with known duplicates for testing deduplication.

    Returns a DataFrame with 5 rows (3 unique, 2 exact duplicates):
    - Row 1: unique
    - Row 2: unique
    - Row 3: exact duplicate of Row 1
    - Row 4: unique
    - Row 5: exact duplicate of Row 2
    """
    return _make_df(
        {
            "Invoice": "INV-1",
            "StockCode": "A",
            "Description": "Prod A",
            "Quantity": "3",
            "InvoiceDate": "2009-12-01 07:45:00",
            "Price": "2.00",
            "Customer ID": "C1",
            "Country": "US",
        },
        {
            "Invoice": "INV-2",
            "StockCode": "B",
            "Description": "Prod B",
            "Quantity": "1",
            "InvoiceDate": "2009-12-01 08:00:00",
            "Price": "5.00",
            "Customer ID": "C2",
            "Country": "US",
        },
        {
            "Invoice": "INV-1",
            "StockCode": "A",
            "Description": "Prod A",
            "Quantity": "3",
            "InvoiceDate": "2009-12-01 07:45:00",
            "Price": "2.00",
            "Customer ID": "C1",
            "Country": "US",
        },
        {
            "Invoice": "INV-3",
            "StockCode": "C",
            "Description": "Prod C",
            "Quantity": "2",
            "InvoiceDate": "2009-12-01 09:00:00",
            "Price": "3.00",
            "Customer ID": "C3",
            "Country": "US",
        },
        {
            "Invoice": "INV-2",
            "StockCode": "B",
            "Description": "Prod B",
            "Quantity": "1",
            "InvoiceDate": "2009-12-01 08:00:00",
            "Price": "5.00",
            "Customer ID": "C2",
            "Country": "US",
        },
    )


# ---------------------------------------------------------------------------
# 1. Column validation
# ---------------------------------------------------------------------------
class TestColumnValidation:
    def test_valid_columns_pass(self):
        df = pd.DataFrame(
            {
                c: ["x"]
                for c in [
                    "Invoice",
                    "StockCode",
                    "Description",
                    "Quantity",
                    "InvoiceDate",
                    "Price",
                    "Customer ID",
                    "Country",
                ]
            }
        )
        validate_columns(df, cleaner.EXPECTED_COLUMNS)  # should not raise

    def test_missing_columns_raise_error(self):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        with pytest.raises(ValueError, match="Missing expected columns"):
            validate_columns(df, cleaner.EXPECTED_COLUMNS)

    def test_unexpected_columns_raise_error(self):
        data = {c: [str(i) for i in range(2)] for c in cleaner.EXPECTED_COLUMNS}
        data["Extra"] = ["99", "98"]
        df = pd.DataFrame(data)
        with pytest.raises(ValueError, match="Unexpected extra columns"):
            validate_columns(df, cleaner.EXPECTED_COLUMNS)


# ---------------------------------------------------------------------------
# 2. Source row ID assignment
# ---------------------------------------------------------------------------
class TestSourceRowIDAssignment:
    def test_ids_start_at_1(self):
        df = pd.DataFrame({"A": ["x", "y", "z"]})
        result = assign_source_row_ids(df)
        assert result["source_row_id"].tolist() == [1, 2, 3]

    def test_ids_are_preserved_in_copy(self):
        df = pd.DataFrame({"A": ["x", "y", "z"]})
        result = assign_source_row_ids(df)
        # Original df should not have source_row_id
        assert "source_row_id" not in df.columns
        # Result should have source_row_id
        assert "source_row_id" in result.columns


# ---------------------------------------------------------------------------
# 3. Negative-price quarantine
# ---------------------------------------------------------------------------
class TestNegativePriceQuarantine:
    def test_negative_price_rows_quarantined(self):
        df = _make_df(
            {"Price": "6.95"},
            {"Price": "-1.00"},
            {"Price": "0"},
        )
        cleaned, quarantined = quarantine_negative_price(df)
        assert len(cleaned) == 2  # 6.95 and 0
        assert len(quarantined) == 1  # -1.00
        assert quarantined.iloc[0]["rejection_reason"] == "negative_price"

    def test_negative_price_and_duplicate_classified_correctly(self):
        """Negative-price rows are quarantined even if they are duplicates.

        With the new order (quarantine first, then deduplicate),
        repeated negative-price rows are classified as negative-price
        quarantine records, NOT as duplicate records.
        """
        df = _make_df(
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "-5.00",
                "Customer ID": "C1",
                "Country": "US",
            },  # row 1
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "-5.00",
                "Customer ID": "C1",
                "Country": "US",
            },  # row 2 (exact duplicate of row 1)
            {
                "Invoice": "INV-2",
                "StockCode": "B",
                "Description": "Prod B",
                "Quantity": "1",
                "InvoiceDate": "2009-12-01 08:00:00",
                "Price": "6.95",
                "Customer ID": "C2",
                "Country": "US",
            },  # row 3 (unique)
        )

        # Step 1: quarantine negative prices first
        cleaned_pre_dedup, quarantined = quarantine_negative_price(df)
        # Both negative-price rows should be quarantined
        assert len(quarantined) == 2
        # Both should have rejection_reason = 'negative_price'
        assert all(quarantined["rejection_reason"] == "negative_price")

        # Step 2: deduplicate among remaining (non-negative-price) records
        cleaned, duplicates = deduplicate_exact(cleaned_pre_dedup)
        # Only 1 row remaining after quarantine (the 6.95 one)
        assert len(cleaned_pre_dedup) == 1
        # No duplicates among the non-negative-price rows
        assert len(duplicates) == 0
        # Final cleaned has 1 row
        assert len(cleaned) == 1


# ---------------------------------------------------------------------------
# 4. Deduplication
# ---------------------------------------------------------------------------
class TestDeduplication:
    def test_exact_duplicates_removed(self):
        """First occurrence is kept; subsequent occurrences are moved."""
        df = _make_duplicate_df()
        unique, duplicates = deduplicate_exact(df)
        # 5 input rows, 2 exact duplicates -> 3 unique, 2 duplicates
        assert len(unique) == 3
        assert len(duplicates) == 2

    def test_first_occurrence_kept(self):
        """The first occurrence of each unique record is kept."""
        df = _make_duplicate_df()
        unique, _ = deduplicate_exact(df)
        # The unique rows should be rows 1, 2, 4 (source_row_ids 1, 2, 4)
        assert unique["source_row_id"].tolist() == [1, 2, 4]

    def test_duplicates_have_source_row_id(self):
        """Duplicate rows must preserve their source_row_id."""
        df = _make_duplicate_df()
        _, duplicates = deduplicate_exact(df)
        assert "source_row_id" in duplicates.columns
        assert duplicates["source_row_id"].tolist() == [3, 5]

    def test_duplicates_use_all_8_source_columns(self):
        """Deduplication compares on all 8 source columns, not source_row_id."""
        # Two rows with same 8 source columns but different source_row_id -> duplicate
        df = _make_df(
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "2.00",
                "Customer ID": "C1",
                "Country": "US",
            },
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "2.00",
                "Customer ID": "C1",
                "Country": "US",
            },
        )
        unique, duplicates = deduplicate_exact(df)
        # source_row_id differs (1 vs 2) but all 8 source columns are identical
        assert len(unique) == 1  # first occurrence kept
        assert len(duplicates) == 1  # second occurrence removed

    def test_no_duplicates_when_all_unique(self):
        """All-unique dataset should have 0 duplicates."""
        df = _make_df(
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "2.00",
                "Customer ID": "C1",
                "Country": "US",
            },
            {
                "Invoice": "INV-2",
                "StockCode": "B",
                "Description": "Prod B",
                "Quantity": "1",
                "InvoiceDate": "2009-12-01 08:00:00",
                "Price": "5.00",
                "Customer ID": "C2",
                "Country": "US",
            },
        )
        unique, duplicates = deduplicate_exact(df)
        assert len(unique) == 2
        assert len(duplicates) == 0

    def test_negative_quantity_and_zero_price_preserved(self):
        """Negative quantities and zero prices are NOT duplicates or rejected."""
        df = _make_df(
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "-5",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "6.95",
                "Customer ID": "C1",
                "Country": "US",
            },
            {
                "Invoice": "INV-2",
                "StockCode": "B",
                "Description": "Prod B",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 08:00:00",
                "Price": "0",
                "Customer ID": "C2",
                "Country": "US",
            },
        )
        unique, duplicates = deduplicate_exact(df)
        # Neither is a duplicate
        assert len(unique) == 2
        assert len(duplicates) == 0


# ---------------------------------------------------------------------------
# 5. Row conservation
# ---------------------------------------------------------------------------
class TestRowConservation:
    def test_conservation_with_duplicates_and_quarantine(self):
        """Input rows == cleaned + negative-price quarantined + duplicates."""
        df = _make_df(
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "2.00",
                "Customer ID": "C1",
                "Country": "US",
            },
            {
                "Invoice": "INV-2",
                "StockCode": "B",
                "Description": "Prod B",
                "Quantity": "1",
                "InvoiceDate": "2009-12-01 08:00:00",
                "Price": "-1.00",
                "Customer ID": "C2",
                "Country": "US",
            },  # neg price
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "2.00",
                "Customer ID": "C1",
                "Country": "US",
            },  # dup of row 1
            {
                "Invoice": "INV-3",
                "StockCode": "C",
                "Description": "Prod C",
                "Quantity": "2",
                "InvoiceDate": "2009-12-01 09:00:00",
                "Price": "3.00",
                "Customer ID": "C3",
                "Country": "US",
            },
        )

        # Step 1: quarantine negative prices first
        cleaned_pre_dedup, quarantined = quarantine_negative_price(df)
        # Step 2: deduplicate among non-negative-price rows
        cleaned, duplicates = deduplicate_exact(cleaned_pre_dedup)

        # Verify conservation: input = cleaned + quarantined + duplicates
        input_count = len(df)
        assert len(cleaned) + len(quarantined) + len(duplicates) == input_count

    def test_conservation_report_fields(self):
        """Cleaning report must contain all required fields."""
        from cleaner import compute_cleaning_report

        df = _make_df(
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "2.00",
                "Customer ID": "C1",
                "Country": "US",
            },
            {
                "Invoice": "INV-2",
                "StockCode": "B",
                "Description": "Prod B",
                "Quantity": "1",
                "InvoiceDate": "2009-12-01 08:00:00",
                "Price": "-1.00",
                "Customer ID": "C2",
                "Country": "US",
            },  # neg price
            {
                "Invoice": "INV-1",
                "StockCode": "A",
                "Description": "Prod A",
                "Quantity": "3",
                "InvoiceDate": "2009-12-01 07:45:00",
                "Price": "2.00",
                "Customer ID": "C1",
                "Country": "US",
            },  # dup of row 1
        )

        cleaned_pre_dedup, quarantined = quarantine_negative_price(df)
        cleaned, duplicates = deduplicate_exact(cleaned_pre_dedup)

        report = compute_cleaning_report(df, cleaned, quarantined, duplicates)

        # Required fields must be present
        assert "input_row_count" in report
        assert "cleaned_row_count" in report
        assert "final_cleaned_row_count" in report
        assert "quarantined_row_count" in report
        assert "negative_price_quarantined_count" in report
        assert "duplicate_rows_removed" in report
        assert "unique_rows_after_dedup" in report
        assert "quarantine_reason_counts" in report
        assert "duplicate_excess_rows_in_input" in report
        assert "negative_quantity_count_cleaned" in report
        assert "zero_price_count_cleaned" in report
        assert "missing_customer_id_count_cleaned" in report
        assert "missing_description_count_cleaned" in report

        # Verify conservation
        assert (
            report["input_row_count"]
            == report["cleaned_row_count"]
            + report["quarantined_row_count"]
            + report["duplicate_rows_removed"]
        )


# ---------------------------------------------------------------------------
# 6. Integration: full cleaning pipeline (small in-memory dataset)
# ---------------------------------------------------------------------------
class TestFullCleaningPipeline:
    def test_full_pipeline_with_mixed_data(self, tmp_path, monkeypatch):
        """End-to-end: read -> validate -> assign IDs -> quarantine -> dedup -> write.

        Uses a small in-memory CSV so no real dataset is touched.
        """
        csv_content = (
            "Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country\n"
            "INV-1,A,Prod A,3,2009-12-01 07:45:00,2.00,C1,US\n"
            "INV-2,B,Prod B,1,2009-12-01 08:00:00,-1.00,C2,US\n"  # negative price -> quarantined
            "INV-1,A,Prod A,3,2009-12-01 07:45:00,2.00,C1,US\n"  # exact dup of row 1 -> removed
            "INV-3,C,Prod C,2,2009-12-01 09:00:00,3.00,C3,US\n"
            "INV-4,D,,5,2009-12-01 10:00:00,4.00,,US\n"  # missing desc + customer_id
        )
        csv_file = tmp_path / "raw_test.csv"
        csv_file.write_text(csv_content)

        cleaned_path = tmp_path / "cleaned.csv"
        quarantined_path = tmp_path / "quarantined.csv"
        duplicates_path = tmp_path / "duplicates.csv"
        report_path = tmp_path / "report.json"

        monkeypatch.setattr(cleaner, "RAW_CSV", csv_file)
        monkeypatch.setattr(cleaner, "CLEANED_PATH", cleaned_path)
        monkeypatch.setattr(cleaner, "QUARANTINED_PATH", quarantined_path)
        monkeypatch.setattr(cleaner, "DUPLICATES_PATH", duplicates_path)
        monkeypatch.setattr(cleaner, "CLEANING_REPORT_PATH", report_path)

        cleaner.run_cleaning()

        # Read outputs
        cleaned_df = pd.read_csv(cleaned_path, dtype=str, keep_default_na=False, na_values=[""])
        quarantined_df = pd.read_csv(
            quarantined_path, dtype=str, keep_default_na=False, na_values=[""]
        )
        duplicates_df = pd.read_csv(
            duplicates_path, dtype=str, keep_default_na=False, na_values=[""]
        )

        # Row conservation: input (5) = cleaned (3) + quarantined (1) + duplicates (1)
        assert len(cleaned_df) == 3  # INV-1 (first), INV-3, INV-4
        assert len(quarantined_df) == 1  # INV-2 (negative price)
        assert len(duplicates_df) == 1  # INV-1 duplicate

        assert len(cleaned_df) + len(quarantined_df) + len(duplicates_df) == 5

        # Negative-price row classified as quarantine, not duplicate
        assert quarantined_df.iloc[0]["rejection_reason"] == "negative_price"

        # Source_row_id preserved in all outputs
        assert "source_row_id" in cleaned_df.columns
        assert "source_row_id" in quarantined_df.columns
        assert "source_row_id" in duplicates_df.columns

        # Cleaned rows have correct source_row_ids (1, 4, 5)
        assert cleaned_df["source_row_id"].tolist() == ["1", "4", "5"]
        # Quarantined row has source_row_id (2)
        assert quarantined_df.iloc[0]["source_row_id"] == "2"
        # Duplicate row has source_row_id (3)
        assert duplicates_df.iloc[0]["source_row_id"] == "3"

        # Missing description and customer_id preserved as NaN in cleaned
        cleaned_last = cleaned_df.iloc[2]  # INV-4 row
        assert pd.isna(cleaned_last["Description"])  # empty -> NaN
        assert pd.isna(cleaned_last["Customer ID"])  # empty -> NaN

    def test_full_pipeline_all_valid(self, tmp_path, monkeypatch):
        """All-valid rows: all go to cleaned, no quarantine or duplicates."""
        csv_content = (
            "Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country\n"
            "INV-1,A,Prod A,2,2009-12-01 07:45:00,10.00,C1,US\n"
            "INV-2,B,Prod B,1,2009-12-01 08:00:00,5.00,C2,US\n"
        )
        csv_file = tmp_path / "raw_ok.csv"
        csv_file.write_text(csv_content)

        cleaned_path = tmp_path / "cleaned.csv"
        quarantined_path = tmp_path / "quarantined.csv"
        duplicates_path = tmp_path / "duplicates.csv"
        report_path = tmp_path / "report.json"

        monkeypatch.setattr(cleaner, "RAW_CSV", csv_file)
        monkeypatch.setattr(cleaner, "CLEANED_PATH", cleaned_path)
        monkeypatch.setattr(cleaner, "QUARANTINED_PATH", quarantined_path)
        monkeypatch.setattr(cleaner, "DUPLICATES_PATH", duplicates_path)
        monkeypatch.setattr(cleaner, "CLEANING_REPORT_PATH", report_path)

        cleaner.run_cleaning()

        cleaned_df = pd.read_csv(cleaned_path, dtype=str, keep_default_na=False, na_values=[""])
        quarantined_df = pd.read_csv(
            quarantined_path, dtype=str, keep_default_na=False, na_values=[""]
        )
        duplicates_df = pd.read_csv(
            duplicates_path, dtype=str, keep_default_na=False, na_values=[""]
        )

        assert len(cleaned_df) == 2
        assert len(quarantined_df) == 0
        assert len(duplicates_df) == 0
        assert len(cleaned_df) + len(quarantined_df) + len(duplicates_df) == 2

    def test_full_pipeline_negative_price_duplicates(self, tmp_path, monkeypatch):
        """Repeated negative-price rows are quarantined, not deduplicated."""
        csv_content = (
            "Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country\n"
            "INV-1,A,Prod A,1,2009-12-01 07:45:00,-5.00,C1,US\n"  # neg price
            "INV-1,A,Prod A,1,2009-12-01 07:45:00,-5.00,C1,US\n"  # exact dup of row 1 (also neg price)
            "INV-2,B,Prod B,2,2009-12-01 08:00:00,6.95,C2,US\n"  # valid
        )
        csv_file = tmp_path / "raw_neg_dup.csv"
        csv_file.write_text(csv_content)

        cleaned_path = tmp_path / "cleaned.csv"
        quarantined_path = tmp_path / "quarantined.csv"
        duplicates_path = tmp_path / "duplicates.csv"
        report_path = tmp_path / "report.json"

        monkeypatch.setattr(cleaner, "RAW_CSV", csv_file)
        monkeypatch.setattr(cleaner, "CLEANED_PATH", cleaned_path)
        monkeypatch.setattr(cleaner, "QUARANTINED_PATH", quarantined_path)
        monkeypatch.setattr(cleaner, "DUPLICATES_PATH", duplicates_path)
        monkeypatch.setattr(cleaner, "CLEANING_REPORT_PATH", report_path)

        cleaner.run_cleaning()

        cleaned_df = pd.read_csv(cleaned_path, dtype=str, keep_default_na=False, na_values=[""])
        quarantined_df = pd.read_csv(
            quarantined_path, dtype=str, keep_default_na=False, na_values=[""]
        )
        duplicates_df = pd.read_csv(
            duplicates_path, dtype=str, keep_default_na=False, na_values=[""]
        )

        # Both negative-price rows are quarantined (not deduplicated)
        assert len(quarantined_df) == 2
        assert all(quarantined_df["rejection_reason"] == "negative_price")
        # No duplicates among the remaining non-negative-price rows
        assert len(duplicates_df) == 0
        # 1 cleaned row (the valid one)
        assert len(cleaned_df) == 1

        # Row conservation
        assert len(cleaned_df) + len(quarantined_df) + len(duplicates_df) == 3
