"""Unit tests for pipeline/scripts/data_quality.py.

All tests use small in-memory pandas DataFrames; no dataset, database, or
transformation code is executed.

Important: to import ``data_quality`` the test directory adds
``pipeline/scripts`` to :data:`sys.path` so that the module can be loaded as a
top-level module regardless of the working directory.
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Ensure data_quality.py is importable from pipeline/scripts regardless of cwd
# ---------------------------------------------------------------------------
_data_quality_src = Path(__file__).resolve().parent.parent / "scripts"
if str(_data_quality_src) not in sys.path:
    sys.path.insert(0, str(_data_quality_src))

import data_quality  # noqa: E402
from data_quality import (  # noqa: E402
    BIGINT_MAX,
    BIGINT_MIN,
    EXPECTED_COLUMNS,
    NULLABLE_COLUMNS,
    REQUIRED_COLUMNS,
    _fits_numeric,
    _parse_bigint,
    _parse_decimal,
    _parse_positive_bigint,
    validate_dataframe,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(**overrides) -> dict[str, str]:
    """Return a valid transformed row, deriving dependent columns on override.

    ``line_total``, ``invoice_date``, and ``invoice_month`` are recomputed from
    overrides unless the caller explicitly supplies them, so most tests only
    need to change the field under test.
    """
    values: dict[str, str] = {
        "source_row_id": "1",
        "invoice": "INV-1",
        "stock_code": "SKU-1",
        "description": "Product 1",
        "quantity": "2",
        "invoice_timestamp": "2009-12-01 07:45:00",
        "price": "6.9500",
        "customer_id": "13085",
        "country": "United Kingdom",
        "invoice_date": "2009-12-01",
        "line_total": "13.9000",
        "invoice_month": "2009-12",
    }
    values.update(overrides)

    if "line_total" not in overrides:
        try:
            total = Decimal(values["quantity"]) * Decimal(values["price"])
            values["line_total"] = f"{total:.4f}"
        except Exception:
            values["line_total"] = "0.0000"

    if "invoice_date" not in overrides or "invoice_month" not in overrides:
        try:
            timestamp = pd.Timestamp(values["invoice_timestamp"])
            if "invoice_date" not in overrides:
                values["invoice_date"] = timestamp.strftime("%Y-%m-%d")
            if "invoice_month" not in overrides:
                values["invoice_month"] = timestamp.strftime("%Y-%m")
        except Exception:
            pass

    return values


def _df(*rows: dict[str, str]) -> pd.DataFrame:
    """Build a DataFrame with the expected column order."""
    return pd.DataFrame(list(rows), columns=EXPECTED_COLUMNS, dtype=str)


def _checks(report: dict) -> dict[str, dict]:
    """Index report checks by rule id."""
    return {check["rule_id"]: check for check in report["checks"]}


# ---------------------------------------------------------------------------
# 1. Valid data and business-rule preservation
# ---------------------------------------------------------------------------


class TestValidData:
    def test_valid_row_passes_every_check(self):
        report = validate_dataframe(_df(_row()))

        assert report["status"] == "passed"
        assert report["total_rows"] == 1
        assert report["total_columns"] == 12
        assert report["summary"]["failed_checks"] == 0
        assert report["summary"]["rows_with_any_failure"] == 0
        assert report["failure_counts"] == {}
        assert all(check["status"] == "passed" for check in report["checks"])

    def test_negative_quantity_is_preserved_not_failed(self):
        report = validate_dataframe(_df(_row(quantity="-5", price="2.0000")))

        assert report["status"] == "passed"
        assert report["business_rule_counts"]["negative_quantity_rows"] == 1

    def test_zero_price_is_preserved_not_failed(self):
        report = validate_dataframe(_df(_row(quantity="3", price="0.0000")))

        assert report["status"] == "passed"
        assert report["business_rule_counts"]["zero_price_rows"] == 1

    def test_missing_description_and_customer_id_are_allowed(self):
        report = validate_dataframe(_df(_row(description="", customer_id="")))

        assert report["status"] == "passed"
        assert report["nullable_column_null_counts"] == {
            "description": 1,
            "customer_id": 1,
        }
        assert report["business_rule_counts"]["missing_description_rows"] == 1
        assert report["business_rule_counts"]["missing_customer_id_rows"] == 1
        assert _checks(report)["DQ-SCHEMA-04"]["status"] == "passed"

    def test_report_contains_required_sections(self):
        report = validate_dataframe(_df(_row()))

        expected_keys = {
            "total_rows",
            "total_columns",
            "expected_columns",
            "status",
            "summary",
            "failure_counts",
            "column_failure_counts",
            "checks",
            "nullable_column_null_counts",
            "business_rule_counts",
        }
        assert expected_keys.issubset(report)
        assert report["summary"]["total_checks"] == len(report["checks"])


# ---------------------------------------------------------------------------
# 2. Required text fields and schema
# ---------------------------------------------------------------------------


class TestRequiredTextFields:
    @pytest.mark.parametrize(
        ("column", "rule_id"),
        [
            ("invoice", "DQ-REC-03"),
            ("stock_code", "DQ-REC-04"),
            ("country", "DQ-REC-05"),
        ],
    )
    def test_blank_required_text_fails(self, column, rule_id):
        report = validate_dataframe(_df(_row(**{column: ""})))
        check = _checks(report)[rule_id]

        assert report["status"] == "failed"
        assert check["status"] == "failed"
        assert check["column"] == column
        assert check["failure_count"] == 1


class TestSchemaValidation:
    def test_missing_column_fails_and_skips_record_checks(self):
        df = _df(_row()).drop(columns=["price"])
        report = validate_dataframe(df)

        assert report["status"] == "failed"
        assert report["total_columns"] == 11
        assert report["record_checks_skipped"] is True
        assert "price" in report["skip_reason"]
        assert _checks(report)["DQ-SCHEMA-01"]["status"] == "failed"

    def test_extra_column_fails_schema_check(self):
        df = _df(_row())
        df["unexpected"] = "x"
        report = validate_dataframe(df)

        assert report["status"] == "failed"
        assert _checks(report)["DQ-SCHEMA-01"]["status"] == "failed"
        assert "record_checks_skipped" not in report

    def test_wrong_column_order_fails(self):
        df = _df(_row())[list(reversed(EXPECTED_COLUMNS))]
        report = validate_dataframe(df)

        assert report["status"] == "failed"
        assert _checks(report)["DQ-SCHEMA-02"]["status"] == "failed"
        assert "record_checks_skipped" not in report

    def test_schema_constants_partition_the_twelve_columns(self):
        assert len(EXPECTED_COLUMNS) == 12
        assert set(REQUIRED_COLUMNS) | set(NULLABLE_COLUMNS) == set(EXPECTED_COLUMNS)
        assert set(REQUIRED_COLUMNS).isdisjoint(NULLABLE_COLUMNS)


# ---------------------------------------------------------------------------
# 3. source_row_id
# ---------------------------------------------------------------------------


class TestSourceRowId:
    @pytest.mark.parametrize("value", ["0", "-1", "1.5", "abc", "", str(2**63)])
    def test_invalid_source_row_id_fails(self, value):
        report = validate_dataframe(_df(_row(source_row_id=value)))
        check = _checks(report)["DQ-REC-01"]

        assert report["status"] == "failed"
        assert check["status"] == "failed"
        assert check["failure_count"] == 1

    @pytest.mark.parametrize("value", ["1", "42", str(2**63 - 1)])
    def test_positive_integer_source_row_id_passes(self, value):
        report = validate_dataframe(_df(_row(source_row_id=value)))

        assert _checks(report)["DQ-REC-01"]["status"] == "passed"

    def test_duplicate_source_row_id_fails(self):
        rows = [
            _row(source_row_id="1", invoice="INV-1"),
            _row(source_row_id="1", invoice="INV-2"),
        ]
        report = validate_dataframe(_df(*rows))
        check = _checks(report)["DQ-REC-02"]

        assert report["status"] == "failed"
        assert check["status"] == "failed"
        assert check["failure_count"] == 2
        assert "1" in check["sample_failures"]

    def test_unique_source_row_ids_pass(self):
        rows = [
            _row(source_row_id="1", invoice="INV-1"),
            _row(source_row_id="2", invoice="INV-2"),
        ]
        report = validate_dataframe(_df(*rows))

        assert _checks(report)["DQ-REC-02"]["status"] == "passed"


# ---------------------------------------------------------------------------
# 4. quantity and price numeric domains
# ---------------------------------------------------------------------------


class TestQuantity:
    @pytest.mark.parametrize("value", ["1.5", "abc", "", str(2**63), str(-(2**63) - 1)])
    def test_invalid_quantity_fails(self, value):
        report = validate_dataframe(_df(_row(quantity=value)))
        check = _checks(report)["DQ-REC-06"]

        assert check["status"] == "failed"
        assert check["failure_count"] == 1

    @pytest.mark.parametrize("value", ["-5", "0", "3", str(BIGINT_MIN), str(BIGINT_MAX)])
    def test_integer_quantity_boundaries_pass(self, value):
        report = validate_dataframe(_df(_row(quantity=value, price="0.0000", line_total="0.0000")))

        assert _checks(report)["DQ-REC-06"]["status"] == "passed"


class TestPrice:
    @pytest.mark.parametrize("value", ["not_a_number", "NaN", "Inf", "-1.0000", ""])
    def test_invalid_or_negative_price_fails(self, value):
        report = validate_dataframe(_df(_row(price=value)))
        check = _checks(report)["DQ-REC-07"]

        assert check["status"] == "failed"
        assert check["failure_count"] == 1

    @pytest.mark.parametrize(
        ("value", "expected_status"),
        [
            ("0.0000", "passed"),
            ("6.9500", "passed"),
            ("99999999.9999", "passed"),
            ("100000000.0000", "failed"),
            ("0.00001", "failed"),
        ],
    )
    def test_price_numeric_12_4_boundaries(self, value, expected_status):
        report = validate_dataframe(_df(_row(quantity="1", price=value)))

        assert _checks(report)["DQ-REC-08"]["status"] == expected_status


# ---------------------------------------------------------------------------
# 5. invoice_timestamp
# ---------------------------------------------------------------------------


class TestInvoiceTimestamp:
    def test_invalid_timestamp_fails_validity_check(self):
        report = validate_dataframe(_df(_row(invoice_timestamp="not-a-date")))
        checks = _checks(report)

        assert checks["DQ-REC-09"]["status"] == "failed"
        assert checks["DQ-REC-10"]["status"] == "passed"

    def test_timezone_aware_timestamp_fails_naive_check(self):
        report = validate_dataframe(_df(_row(invoice_timestamp="2009-12-01 07:45:00+00:00")))
        checks = _checks(report)

        assert checks["DQ-REC-09"]["status"] == "passed"
        assert checks["DQ-REC-10"]["status"] == "failed"

    def test_mixed_naive_and_timezone_aware_timestamps_are_handled(self):
        rows = [
            _row(source_row_id="1", invoice_timestamp="2009-12-01 07:45:00"),
            _row(
                source_row_id="2",
                invoice="INV-2",
                invoice_timestamp="2009-12-02 08:00:00+05:30",
            ),
        ]
        report = validate_dataframe(_df(*rows))
        checks = _checks(report)

        assert checks["DQ-REC-09"]["failure_count"] == 0
        assert checks["DQ-REC-10"]["failure_count"] == 1


# ---------------------------------------------------------------------------
# 6. Derived columns
# ---------------------------------------------------------------------------


class TestDerivedColumns:
    def test_invoice_date_mismatch_fails(self):
        report = validate_dataframe(_df(_row(invoice_date="2009-12-02")))

        assert _checks(report)["DQ-DER-01"]["status"] == "failed"

    def test_invoice_month_mismatch_fails(self):
        report = validate_dataframe(_df(_row(invoice_month="2009-11")))

        assert _checks(report)["DQ-DER-02"]["status"] == "failed"

    def test_line_total_mismatch_fails(self):
        report = validate_dataframe(_df(_row(line_total="99.9999")))

        assert _checks(report)["DQ-DER-03"]["status"] == "failed"

    def test_decimal_safe_line_total_comparison_passes(self):
        report = validate_dataframe(_df(_row(quantity="3", price="3.3300")))

        assert report["status"] == "passed"
        assert _checks(report)["DQ-DER-03"]["status"] == "passed"

    def test_float_artifact_in_line_total_fails(self):
        report = validate_dataframe(
            _df(
                _row(
                    quantity="3",
                    price="0.1000",
                    line_total="0.30000000000000004",
                )
            )
        )
        checks = _checks(report)

        assert checks["DQ-DER-03"]["status"] == "failed"
        assert checks["DQ-DER-04"]["status"] == "failed"

    def test_line_total_numeric_14_4_boundary_passes(self):
        report = validate_dataframe(_df(_row(quantity="1", price="99999999.9999")))

        assert _checks(report)["DQ-DER-04"]["status"] == "passed"

    def test_line_total_exceeding_numeric_14_4_fails(self):
        report = validate_dataframe(_df(_row(quantity="99999999", price="9999.9999")))
        checks = _checks(report)

        assert checks["DQ-DER-03"]["status"] == "passed"
        assert checks["DQ-DER-04"]["status"] == "failed"


# ---------------------------------------------------------------------------
# 7. Report aggregation
# ---------------------------------------------------------------------------


class TestReportAggregation:
    def test_rows_with_any_failure_is_deduplicated_across_checks(self):
        rows = [
            _row(source_row_id="1", invoice=""),
            _row(source_row_id="2", invoice="", invoice_month="2009-11"),
        ]
        report = validate_dataframe(_df(*rows))

        assert report["summary"]["rows_with_any_failure"] == 2
        assert report["summary"]["total_failure_count"] > 2
        assert report["column_failure_counts"]["invoice"] >= 2

    def test_failure_counts_identify_rule_and_column(self):
        report = validate_dataframe(_df(_row(price="-1.0000")))
        checks = _checks(report)

        assert report["failure_counts"]["DQ-REC-07"] == 1
        assert report["column_failure_counts"]["price"] >= 1
        assert checks["DQ-REC-07"]["column"] == "price"

    def test_run_validation_writes_json_report(self, tmp_path):
        input_path = tmp_path / "transformed.csv"
        report_path = tmp_path / "quality.json"
        _df(_row()).to_csv(input_path, index=False)

        report = data_quality.run_validation(
            input_path=input_path,
            report_path=report_path,
        )

        assert report_path.is_file()
        loaded = json.loads(report_path.read_text(encoding="utf-8"))
        assert loaded["status"] == "passed"
        assert loaded["total_rows"] == 1
        assert loaded["input_path"] == str(input_path)
        assert report["status"] == "passed"

    def test_main_exits_nonzero_when_report_fails(self, monkeypatch):
        monkeypatch.setattr(data_quality, "run_validation", lambda: {"status": "failed"})

        with pytest.raises(SystemExit) as exc_info:
            data_quality.main()

        assert exc_info.value.code == 1

    def test_main_returns_normally_when_report_passes(self, monkeypatch):
        monkeypatch.setattr(data_quality, "run_validation", lambda: {"status": "passed"})

        data_quality.main()  # should not raise


# ---------------------------------------------------------------------------
# 8. Public helper functions and parsing boundaries
# ---------------------------------------------------------------------------


class TestPublicHelpers:
    def test_validate_records_returns_checks_and_mask(self):
        checks, mask = data_quality.validate_records(_df(_row()))

        assert len(checks) == 10
        assert not mask.any()

    def test_validate_derived_columns_returns_checks_and_mask(self):
        checks, mask = data_quality.validate_derived_columns(_df(_row()))

        assert len(checks) == 4
        assert not mask.any()

    def test_validate_schema_returns_schema_checks(self):
        checks = data_quality.validate_schema(_df(_row()))

        assert len(checks) == 4
        assert all(check.passed for check in checks)


class TestParsingHelpers:
    def test_parse_positive_bigint_boundaries(self):
        assert _parse_positive_bigint("1") == 1
        assert _parse_positive_bigint(str(BIGINT_MAX)) == BIGINT_MAX
        assert _parse_positive_bigint("0") is None
        assert _parse_positive_bigint(str(BIGINT_MAX + 1)) is None
        assert _parse_positive_bigint("1.5") is None
        assert _parse_positive_bigint("") is None

    def test_parse_bigint_boundaries(self):
        assert _parse_bigint(str(BIGINT_MIN)) == BIGINT_MIN
        assert _parse_bigint(str(BIGINT_MAX)) == BIGINT_MAX
        assert _parse_bigint(str(BIGINT_MAX + 1)) is None
        assert _parse_bigint("1.5") is None

    def test_parse_decimal_rejects_non_finite_and_blank(self):
        assert _parse_decimal("1.2300") == Decimal("1.2300")
        assert _parse_decimal("-1.0000") == Decimal("-1.0000")
        assert _parse_decimal("NaN") is None
        assert _parse_decimal("Inf") is None
        assert _parse_decimal("") is None
        assert _parse_decimal(None) is None

    @pytest.mark.parametrize(
        ("value", "precision", "scale", "expected"),
        [
            (Decimal("0"), 12, 4, True),
            (Decimal("6.9500"), 12, 4, True),
            (Decimal("99999999.9999"), 12, 4, True),
            (Decimal("100000000.0000"), 12, 4, False),
            (Decimal("0.00001"), 12, 4, False),
            (Decimal("-1.0000"), 12, 4, True),
        ],
    )
    def test_fits_numeric(self, value, precision, scale, expected):
        assert _fits_numeric(value, precision, scale) is expected
