"""Unit tests for pipeline/scripts/transformer.py.

All LLM, embedding, and database calls are avoided. Tests use small
in-memory pandas DataFrames and directly import transformer functions.
No actual dataset rows are read; ``pytest.fixture`` and
``pytest.mark.parametrize`` are used for coverage and readability.

Important: to import ``transformer`` the test directory adds
``pipeline/scripts`` to :data:`sys.path` so that the module can be
loaded as a top-level module regardless of the working directory.
"""

import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Ensure transformer.py is importable from pipeline/scripts regardless of cwd
# ---------------------------------------------------------------------------
_transformer_src = Path(__file__).resolve().parent.parent / "scripts"
if str(_transformer_src) not in sys.path:
    sys.path.insert(0, str(_transformer_src))

import transformer  # noqa: E402
from transformer import (  # noqa: E402
    EXPECTED_INPUT_COLUMNS,
    REQUIRED_FIELDS,
    _fits_numeric,
    _parse_price,
    _parse_quantity,
    _parse_source_row_id,
    _parse_timestamp,
    transform_row,
    validate_input_columns,
    validate_source_row_id_unique,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_row(overrides: dict | None = None) -> pd.Series:
    """Return a minimal valid input row Series with all EXPECTED_INPUT_COLUMNS.

    *overrides* is a dict mapping column names (with spaces) to string values;
    columns not present use defaults.
    """
    default = {
        "Invoice": "INV-1",
        "StockCode": "SKU-1",
        "Description": "Product 1",
        "Quantity": "2",
        "InvoiceDate": "2009-12-01 07:45:00",
        "Price": "6.95",
        "Customer ID": "13085",
        "Country": "United Kingdom",
        "source_row_id": "1",
    }
    if overrides:
        default.update(overrides)
    return pd.Series(default, dtype=str)


def _write_cleaned_csv(path: Path, rows: list[dict]) -> None:
    """Write a small cleaned CSV with EXPECTED_INPUT_COLUMNS headers."""
    df = pd.DataFrame(rows, columns=EXPECTED_INPUT_COLUMNS, dtype=str)
    df.to_csv(path, index=False, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Successful transformation
# ---------------------------------------------------------------------------
class TestSuccessfulTransformation:
    def test_valid_row_transforms_successfully(self):
        row = _valid_row()
        record, reason = transform_row(row)
        assert reason is None
        assert record["source_row_id"] == 1
        assert record["invoice"] == "INV-1"
        assert record["stock_code"] == "SKU-1"
        assert record["description"] == "Product 1"
        assert record["quantity"] == 2
        assert record["price"] == "6.9500"
        assert record["invoice_date"] == "2009-12-01"
        assert record["invoice_month"] == "2009-12"
        assert record["invoice_timestamp"] == "2009-12-01 07:45:00"
        assert record["customer_id"] == "13085"
        assert record["country"] == "United Kingdom"
        assert record["line_total"] == "13.9000"

    def test_source_row_id_preserved_as_int(self):
        row = _valid_row({"source_row_id": "42"})
        record, reason = transform_row(row)
        assert reason is None
        assert record["source_row_id"] == 42
        assert isinstance(record["source_row_id"], int)

    def test_text_fields_are_trimmed(self):
        row = _valid_row(
            {
                "Invoice": "  INV-9  ",
                "StockCode": " SKU-9 ",
                "Description": "  Prod  ",
                "Country": "  UK ",
            }
        )
        record, reason = transform_row(row)
        assert reason is None
        assert record["invoice"] == "INV-9"
        assert record["stock_code"] == "SKU-9"
        assert record["description"] == "Prod"
        assert record["country"] == "UK"

    def test_invoice_rows_preserved_no_aggregation(self):
        """Multiple rows sharing the same invoice are preserved, not aggregated."""
        rows = [
            _valid_row({"Invoice": "INV-1", "StockCode": "A", "Quantity": "3", "Price": "2.00", "source_row_id": "1"}),
            _valid_row({"Invoice": "INV-1", "StockCode": "B", "Quantity": "1", "Price": "5.50", "source_row_id": "2"}),
            _valid_row({"Invoice": "INV-2", "StockCode": "A", "Quantity": "2", "Price": "2.00", "source_row_id": "3"}),
        ]
        records = []
        for r in rows:
            rec, reason = transform_row(r)
            assert reason is None, f"Unexpected rejection: {reason}"
            records.append(rec)

        assert len({r["source_row_id"] for r in records}) == len(records)
        invoices = [r["invoice"] for r in records]
        assert invoices.count("INV-1") == 2  # both preserved, not collapsed
        assert invoices.count("INV-2") == 1


# ---------------------------------------------------------------------------
# 2. Derived columns
# ---------------------------------------------------------------------------
class TestDerivedColumns:
    def test_invoice_date_extracted(self):
        record, _ = transform_row(_valid_row())
        assert record["invoice_date"] == "2009-12-01"

    def test_invoice_month_derived(self):
        record, _ = transform_row(_valid_row({"InvoiceDate": "2009-12-31 23:59:59"}))
        assert record["invoice_month"] == "2009-12"

    def test_invoice_month_other_month(self):
        record, _ = transform_row(_valid_row({"InvoiceDate": "2010-01-01 00:00:00"}))
        assert record["invoice_month"] == "2010-01"

    def test_line_total_equals_quantity_times_price(self):
        record, _ = transform_row(_valid_row({"Quantity": "2", "Price": "6.95"}))
        assert record["line_total"] == "13.9000"

    def test_line_total_decimal_precision(self):
        # 3 * 3.33 = 9.9900 exactly
        record, _ = transform_row(_valid_row({"Quantity": "3", "Price": "3.33"}))
        assert record["line_total"] == "9.9900"

    def test_line_total_single_cent(self):
        # 1 * 0.10 = 0.1000
        record, _ = transform_row(_valid_row({"Quantity": "1", "Price": "0.10"}))
        assert record["line_total"] == "0.1000"


# ---------------------------------------------------------------------------
# 3. Nullable fields
# ---------------------------------------------------------------------------
class TestNullableFields:
    def test_missing_description_is_null(self):
        record, reason = transform_row(_valid_row({"Description": ""}))
        assert reason is None
        assert record["description"] is None

    def test_missing_customer_id_is_null(self):
        record, reason = transform_row(_valid_row({"Customer ID": ""}))
        assert reason is None
        assert record["customer_id"] is None


# ---------------------------------------------------------------------------
# 4. Business rules
# ---------------------------------------------------------------------------
class TestBusinessRules:
    def test_negative_quantity_accepted(self):
        record, reason = transform_row(_valid_row({"Quantity": "-5"}))
        assert reason is None
        assert record["quantity"] == -5

    def test_zero_price_accepted(self):
        record, reason = transform_row(_valid_row({"Price": "0"}))
        assert reason is None
        assert record["price"] == "0.0000"
        assert record["line_total"] == "0.0000"


# ---------------------------------------------------------------------------
# 5. Required-field validation
# ---------------------------------------------------------------------------
class TestRequiredFields:
    @pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
    def test_missing_required_field_rejected(self, missing_field):
        row = _valid_row({missing_field: ""})
        record, reason = transform_row(row)
        assert reason == "missing_required_field"
        assert record is None

    def test_all_required_fields_constant_matches_schema(self):
        # REQUIRED_FIELDS must not include nullable or derived-only columns
        assert "Description" not in REQUIRED_FIELDS
        assert "Customer ID" not in REQUIRED_FIELDS


# ---------------------------------------------------------------------------
# 6. Numeric validation
# ---------------------------------------------------------------------------
class TestNumericValidation:
    @pytest.mark.parametrize("bad_qty", ["1.5", "abc"])
    def test_invalid_and_fractional_quantities_rejected(self, bad_qty):
        record, reason = transform_row(_valid_row({"Quantity": bad_qty}))
        assert record is None
        assert reason == "invalid_quantity"

    def test_empty_quantity_is_missing_required_field(self):
        # Empty Quantity string is caught by required-field check first
        record, reason = transform_row(_valid_row({"Quantity": ""}))
        assert record is None
        assert reason == "missing_required_field"

    def test_quantity_bigint_minimum_boundary_accepted(self):
        # BIGINT_MIN itself is a valid integer within range
        result = _parse_quantity(str(-(2**63)))
        assert result == -(2**63)

    def test_quantity_bigint_maximum_boundary_accepted(self):
        result = _parse_quantity(str(2**63 - 1))
        assert result == 2**63 - 1

    def test_quantity_below_bigint_min_rejected(self):
        record, reason = transform_row(_valid_row({"Quantity": str(-(2**63) - 1)}))
        assert record is None
        assert reason == "invalid_quantity"

    def test_quantity_above_bigint_max_rejected(self):
        record, reason = transform_row(_valid_row({"Quantity": str(2**63)}))
        assert record is None
        assert reason == "invalid_quantity"

    def test_invalid_price_rejected(self):
        record, reason = transform_row(_valid_row({"Price": "not_a_number"}))
        assert record is None
        assert reason == "invalid_price"

    def test_nan_price_rejected(self):
        record, reason = transform_row(_valid_row({"Price": "NaN"}))
        assert record is None
        assert reason == "invalid_price"

    def test_infinity_price_rejected(self):
        record, reason = transform_row(_valid_row({"Price": "Inf"}))
        assert record is None
        assert reason == "invalid_price"

    @pytest.mark.parametrize(
        "price_str, fits",
        [
            ("0", True),
            ("0.0000", True),
            ("6.95", True),
            ("99999999.9999", True),   # 8 integer digits + 4 decimals = 12 total
            ("123456789.99", False),   # 9 integer digits > 8
            ("0.00001", False),        # scale 5 > 4
        ],
    )
    def test_price_numeric12_4_boundaries(self, price_str, fits):
        if fits:
            price = _parse_price(price_str)
            assert isinstance(price, Decimal)
        else:
            with pytest.raises(ValueError, match="price does not fit NUMERIC"):
                _parse_price(price_str)


class TestLineTotalBoundaries:
    @staticmethod
    def _line_total(qty: int, price_str: str) -> Decimal:
        return Decimal(qty) * _parse_price(price_str)

    def test_line_total_fits_numeric14_4(self):
        # 3 * 3.3333 = 9.9999 -> fits
        assert _fits_numeric(self._line_total(3, "3.3333"), 14, 4) is True

    def test_line_total_exact_boundary(self):
        # 1 * 99999999.9999 = 99999999.9999 -> 8 int digits + 4 decimals = 12 total -> fits
        assert _fits_numeric(self._line_total(1, "99999999.9999"), 14, 4) is True

    def test_line_total_exceeds_numeric14_4(self):
        # qty=99999999 * price=9999.9999 -> ~9.999e11, 12 integer digits > 10 -> exceeds
        assert _fits_numeric(self._line_total(99999999, "9999.9999"), 14, 4) is False

    def test_line_total_out_of_range_rejected_in_row(self):
        # quantity huge * price -> line_total exceeds NUMERIC(14,4) -> rejected
        record, reason = transform_row(_valid_row({"Quantity": "99999999", "Price": "9999.9999"}))
        assert record is None
        assert reason == "line_total_out_of_range"


# ---------------------------------------------------------------------------
# 7. Timestamp validation
# ---------------------------------------------------------------------------
class TestTimestampValidation:
    def test_valid_timestamp_accepted(self):
        record, reason = transform_row(_valid_row())
        assert reason is None
        assert record["invoice_timestamp"] == "2009-12-01 07:45:00"

    def test_invalid_timestamp_rejected(self):
        record, reason = transform_row(_valid_row({"InvoiceDate": "not-a-date"}))
        assert record is None
        assert reason == "invalid_timestamp"

    def test_timezone_aware_timestamp_rejected(self):
        record, reason = transform_row(_valid_row({"InvoiceDate": "2009-12-01 07:45:00+00:00"}))
        assert record is None
        assert reason == "timestamp_has_timezone"

    def test_parse_timestamp_returns_reason(self):
        ts, reason = _parse_timestamp("2009-12-01 07:45:00")
        assert ts is not None and reason is None
        ts, reason = _parse_timestamp("garbage")
        assert ts is None and reason == "invalid_timestamp"
        ts, reason = _parse_timestamp("2009-12-01 07:45:00+05:30")
        assert ts is None and reason == "timestamp_has_timezone"


# ---------------------------------------------------------------------------
# 8. Source row ID validation
# ---------------------------------------------------------------------------
class TestSourceRowIDValidation:
    @pytest.mark.parametrize("bad_srid", ["0", "-1", "1.5", "abc", "", "  ", str(2**63)])
    def test_invalid_source_row_id_rejected(self, bad_srid):
        record, reason = transform_row(_valid_row({"source_row_id": bad_srid}))
        assert record is None
        assert reason == "invalid_source_row_id"

    def test_positive_integer_accepted(self):
        record, reason = transform_row(_valid_row({"source_row_id": "42"}))
        assert reason is None
        assert record["source_row_id"] == 42

    def test_bigint_max_source_row_id_accepted(self):
        record, reason = transform_row(_valid_row({"source_row_id": str(2**63 - 1)}))
        assert reason is None
        assert record["source_row_id"] == 2**63 - 1

    def test_leading_zeros_normalised(self):
        # "001" and "1" both parse to the same normalised integer
        assert _parse_source_row_id("001") == 1
        assert _parse_source_row_id("1") == 1

    def test_leading_zeros_treated_as_duplicates(self):
        df = pd.DataFrame({"source_row_id": ["1", "01", "001"]})
        with pytest.raises(RuntimeError, match="Duplicate source_row_id"):
            validate_source_row_id_unique(df)

    def test_duplicate_ids_detected(self):
        df = pd.DataFrame({"source_row_id": ["1", "2", "1"]})
        with pytest.raises(RuntimeError, match="Duplicate source_row_id"):
            validate_source_row_id_unique(df)

    @pytest.mark.parametrize(
        "valid_ids",
        [["1", "2", "3"], ["10", "20", "30"], ["1", "2", "3", "4", "5"]],
    )
    def test_unique_ids_pass(self, valid_ids):
        df = pd.DataFrame({"source_row_id": valid_ids})
        validate_source_row_id_unique(df)  # should not raise

    def test_large_bigint_no_float_precision_loss(self):
        # 2**53+1 is not exactly representable as float64; Decimal keeps it exact
        big = 2**53 + 1
        df = pd.DataFrame({"source_row_id": [str(big), str(big + 1)]})
        validate_source_row_id_unique(df)  # distinct -> no raise
        # and the duplicate of the exact value must be detected
        df_dup = pd.DataFrame({"source_row_id": [str(big), str(big)]})
        with pytest.raises(RuntimeError, match="Duplicate source_row_id"):
            validate_source_row_id_unique(df_dup)

    def test_non_numeric_ids_left_to_row_validation(self):
        # validate_source_row_id_unique must not raise on junk; row-level rejects them
        df = pd.DataFrame({"source_row_id": ["abc", "1.5", "", "nan"]})
        validate_source_row_id_unique(df)  # should not raise
        # row-level validation rejects them individually
        for junk in ["abc", "1.5", ""]:
            record, reason = transform_row(_valid_row({"source_row_id": junk}))
            assert reason == "invalid_source_row_id"


# ---------------------------------------------------------------------------
# 9. Dataset validation
# ---------------------------------------------------------------------------
class TestDatasetValidation:
    def test_expected_input_columns_pass(self):
        df = pd.DataFrame({c: ["x"] for c in EXPECTED_INPUT_COLUMNS})
        validate_input_columns(df, EXPECTED_INPUT_COLUMNS)  # should not raise

    def test_missing_columns_raise_error(self):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        with pytest.raises(ValueError, match="Missing expected columns"):
            validate_input_columns(df, EXPECTED_INPUT_COLUMNS)

    def test_unexpected_columns_raise_error(self):
        data = {c: [str(i) for i in range(2)] for c in EXPECTED_INPUT_COLUMNS}
        data["Extra"] = ["99", "98"]
        df = pd.DataFrame(data)
        with pytest.raises(ValueError, match="Unexpected extra columns"):
            validate_input_columns(df, EXPECTED_INPUT_COLUMNS)

    def test_row_conservation_with_rejections(self, tmp_path, monkeypatch):
        """Input rows == transformed rows + rejected rows (mixed valid/invalid)."""
        csv_file = tmp_path / "cleaned_test.csv"
        rows = [
            {"Invoice": "INV-1", "StockCode": "A", "Description": "Prod A", "Quantity": "3",
             "InvoiceDate": "2009-12-01 07:45:00", "Price": "2.00", "Customer ID": "C1",
             "Country": "US", "source_row_id": "1"},  # valid
            {"Invoice": "INV-2", "StockCode": "B", "Description": "", "Quantity": "5",
             "InvoiceDate": "2009-12-01 08:00:00", "Price": "5.00", "Customer ID": "C2",
             "Country": "US", "source_row_id": "2"},  # missing Quantity? no, quantity present -> valid (desc null ok)
            {"Invoice": "INV-3", "StockCode": "C", "Description": "Prod C", "Quantity": "1",
             "InvoiceDate": "invalid-date", "Price": "1.00", "Customer ID": "C3",
             "Country": "US", "source_row_id": "3"},  # invalid timestamp -> rejected
            {"Invoice": "", "StockCode": "D", "Description": "Prod D", "Quantity": "1",
             "InvoiceDate": "2009-12-01 09:00:00", "Price": "1.00", "Customer ID": "C4",
             "Country": "US", "source_row_id": "4"},  # missing Invoice -> rejected
        ]
        _write_cleaned_csv(csv_file, rows)

        transformed_path = tmp_path / "transformed.csv"
        rejected_path = tmp_path / "rejected.csv"
        report_path = tmp_path / "report.json"

        monkeypatch.setattr(transformer, "CLEANED_INPUT", csv_file)
        monkeypatch.setattr(transformer, "TRANSFORMED_PATH", transformed_path)
        monkeypatch.setattr(transformer, "REJECTED_PATH", rejected_path)
        monkeypatch.setattr(transformer, "REPORT_PATH", report_path)

        transformer.run_transformation()

        transformed_df = pd.read_csv(transformed_path, dtype=str, keep_default_na=False, na_values=[""])
        rejected_df = pd.read_csv(rejected_path, dtype=str, keep_default_na=False, na_values=[""])

        input_count = len(rows)
        assert len(transformed_df) + len(rejected_df) == input_count
        assert len(transformed_df) == 2  # INV-1, INV-2 valid
        assert len(rejected_df) == 2   # INV-3, INV-4 rejected

    def test_row_conservation_all_valid(self, tmp_path, monkeypatch):
        """All-valid rows: input == transformed, rejected is empty."""
        csv_file = tmp_path / "cleaned_ok.csv"
        rows = [
            {"Invoice": "INV-1", "StockCode": "A", "Description": "Prod A", "Quantity": "2",
             "InvoiceDate": "2009-12-01 07:45:00", "Price": "10.00", "Customer ID": "C1",
             "Country": "US", "source_row_id": "1"},
            {"Invoice": "INV-2", "StockCode": "B", "Description": "Prod B", "Quantity": "1",
             "InvoiceDate": "2009-12-01 08:00:00", "Price": "5.00", "Customer ID": "C2",
             "Country": "US", "source_row_id": "2"},
        ]
        _write_cleaned_csv(csv_file, rows)

        transformed_path = tmp_path / "transformed.csv"
        rejected_path = tmp_path / "rejected.csv"
        report_path = tmp_path / "report.json"

        monkeypatch.setattr(transformer, "CLEANED_INPUT", csv_file)
        monkeypatch.setattr(transformer, "TRANSFORMED_PATH", transformed_path)
        monkeypatch.setattr(transformer, "REJECTED_PATH", rejected_path)
        monkeypatch.setattr(transformer, "REPORT_PATH", report_path)

        transformer.run_transformation()

        transformed_df = pd.read_csv(transformed_path, dtype=str, keep_default_na=False, na_values=[""])
        rejected_df = pd.read_csv(rejected_path, dtype=str, keep_default_na=False, na_values=[""])

        assert len(transformed_df) == 2
        assert len(rejected_df) == 0
        assert len(transformed_df) + len(rejected_df) == 2