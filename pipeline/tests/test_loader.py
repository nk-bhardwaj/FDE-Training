"""Unit tests for pipeline/scripts/loader.py.

All database interactions are mocked. Tests use small temporary CSV files and
fake psycopg connections/cursors, so no Neon connection or real load occurs.

Important: to import ``loader`` the test directory adds ``pipeline/scripts`` to
:data:`sys.path` so the module can be loaded as a top-level module regardless of
the working directory.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Ensure loader.py is importable from pipeline/scripts regardless of cwd
# ---------------------------------------------------------------------------
_loader_src = Path(__file__).resolve().parent.parent / "scripts"
if str(_loader_src) not in sys.path:
    sys.path.insert(0, str(_loader_src))

import loader  # noqa: E402
from loader import (  # noqa: E402
    EXPECTED_COLUMNS,
    LoaderError,
    count_staging_rows,
    count_table_rows,
    create_staging_table,
    find_duplicate_source_row_ids,
    get_dsn,
    inspect_csv,
    run_load,
    stream_csv_to_copy,
    upsert_staging,
    write_json_report,
)

# ---------------------------------------------------------------------------
# Helpers and fakes
# ---------------------------------------------------------------------------


def _row(**overrides: str) -> dict[str, str]:
    """Return one valid transformed row."""
    values = {
        "source_row_id": "1",
        "invoice": "INV-1",
        "stock_code": "SKU-1",
        "description": "Product 1",
        "quantity": "2",
        "invoice_timestamp": "2009-12-01 07:45:00",
        "price": "6.9500",
        "customer_id": "13085.0",
        "country": "United Kingdom",
        "invoice_date": "2009-12-01",
        "line_total": "13.9000",
        "invoice_month": "2009-12",
    }
    values.update(overrides)
    return values


def _write_csv(
    path: Path,
    rows: list[dict[str, str]],
    header: list[str] | None = None,
) -> None:
    """Write a transformed-shaped CSV with the given header and rows."""
    columns = header or EXPECTED_COLUMNS
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _responses(
    *,
    staged: int,
    duplicates: list[tuple[int]] | None = None,
    upsert: object = (0, 0),
    final: int = 0,
) -> list[tuple[str, object]]:
    """Build FakeCursor responses keyed by distinctive SQL fragments."""
    return [
        ("SELECT COUNT(*) FROM staging_cleaned_retail", (staged,)),
        ("GROUP BY source_row_id", duplicates or []),
        ("ON CONFLICT (source_row_id) DO UPDATE", upsert),
        ("SELECT COUNT(*) FROM warehouse.cleaned_online_retail_ii", (final,)),
    ]


class FakeCopy:
    """Minimal stand-in for psycopg's COPY context manager."""

    def __init__(self, sql: str) -> None:
        self.sql = sql
        self.chunks: list[bytes] = []
        self.exited = False

    def __enter__(self) -> FakeCopy:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        self.exited = True
        return False

    def write(self, data: bytes | str) -> None:
        self.chunks.append(data if isinstance(data, bytes) else data.encode("utf-8"))

    @property
    def data(self) -> bytes:
        return b"".join(self.chunks)


class FakeCursor:
    """Cursor fake that returns configured results for matching SQL fragments."""

    def __init__(self, responses: list[tuple[str, object]] | None = None) -> None:
        self.responses = list(responses or [])
        self.executed: list[tuple[str, object]] = []
        self.copies: list[FakeCopy] = []
        self._result: object = None
        self.closed = False

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        self.closed = True
        return False

    def execute(self, sql: str, params: object = None) -> None:
        self.executed.append((sql, params))
        self._result = None
        for needle, result in self.responses:
            if needle in sql:
                self._result = result
                break

    def _resolve(self) -> object:
        if callable(self._result):
            return self._result()
        return self._result

    def fetchone(self) -> object:
        result = self._resolve()
        if isinstance(result, list):
            return result[0] if result else None
        return result

    def fetchall(self) -> list[object]:
        result = self._resolve()
        if result is None:
            return []
        if isinstance(result, list):
            return result
        return [result]

    def copy(self, sql: str) -> FakeCopy:
        copy = FakeCopy(sql)
        self.copies.append(copy)
        return copy


class FakeConnection:
    """Connection fake that records commit/rollback from the context manager."""

    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        if exc_type is None:
            self.committed = True
        else:
            self.rolled_back = True
        self.closed = True
        return False

    def cursor(self) -> FakeCursor:
        return self._cursor


class FakeFactory:
    """Callable connection factory used in place of ``psycopg.connect``."""

    def __init__(self, cursor: FakeCursor) -> None:
        self.connection = FakeConnection(cursor)
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, dsn: str, **kwargs: object) -> FakeConnection:
        self.calls.append((dsn, kwargs))
        return self.connection


# ---------------------------------------------------------------------------
# 1. CSV inspection
# ---------------------------------------------------------------------------


class TestCsvInspection:
    def test_valid_header_and_row_count(self, tmp_path):
        path = tmp_path / "data.csv"
        _write_csv(
            path,
            [_row(source_row_id="1"), _row(source_row_id="2", invoice="INV-2")],
        )

        header, count = inspect_csv(path)

        assert header == EXPECTED_COLUMNS
        assert count == 2

    def test_reordered_header_is_rejected(self, tmp_path):
        header = list(EXPECTED_COLUMNS)
        header[2], header[3] = header[3], header[2]
        path = tmp_path / "data.csv"
        _write_csv(path, [], header=header)

        with pytest.raises(LoaderError, match="header"):
            inspect_csv(path)

    def test_empty_file_is_rejected(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("", encoding="utf-8")

        with pytest.raises(LoaderError, match="empty"):
            inspect_csv(path)


# ---------------------------------------------------------------------------
# 2. COPY into staging
# ---------------------------------------------------------------------------


class TestCopy:
    def test_copy_streams_rows_and_skips_header(self, tmp_path):
        path = tmp_path / "data.csv"
        _write_csv(path, [_row()])
        cursor = FakeCursor()

        stream_csv_to_copy(cursor, path)

        assert len(cursor.copies) == 1
        copy = cursor.copies[0]
        assert "COPY staging_cleaned_retail" in copy.sql
        assert "FORMAT CSV" in copy.sql
        assert "HEADER FALSE" in copy.sql
        assert "source_row_id" in copy.sql
        assert "loaded_at" not in copy.sql
        assert copy.exited is True
        assert "source_row_id" not in copy.data.decode("utf-8")

    def test_nullable_fields_are_preserved_as_empty_csv_fields(self, tmp_path):
        path = tmp_path / "data.csv"
        _write_csv(path, [_row(description="", customer_id="")])
        cursor = FakeCursor()

        stream_csv_to_copy(cursor, path)

        data = cursor.copies[0].data.decode("utf-8")
        assert ",,2," in data
        assert ",,United Kingdom" in data
        assert "None" not in data
        assert "nan" not in data.lower()

    def test_decimal_precision_is_preserved_as_text(self, tmp_path):
        path = tmp_path / "data.csv"
        _write_csv(path, [_row(price="6.9500", line_total="13.9000")])
        cursor = FakeCursor()

        stream_csv_to_copy(cursor, path)

        data = cursor.copies[0].data.decode("utf-8")
        assert "6.9500" in data
        assert "13.9000" in data


# ---------------------------------------------------------------------------
# 3. Staging and upsert SQL
# ---------------------------------------------------------------------------


class TestStaging:
    def test_staging_table_is_temporary_and_commit_scoped(self):
        cursor = FakeCursor()

        create_staging_table(cursor)

        sql = cursor.executed[0][0]
        assert "CREATE TEMP TABLE" in sql
        assert "LIKE warehouse.cleaned_online_retail_ii" in sql
        assert "INCLUDING DEFAULTS" in sql
        assert "EXCLUDING INDEXES" in sql
        assert "ON COMMIT DROP" in sql
        assert "PRIMARY KEY" not in sql


class TestUpsert:
    def test_upsert_uses_source_row_id_and_refreshes_loaded_at(self):
        cursor = FakeCursor([("ON CONFLICT (source_row_id) DO UPDATE", (2, 1))])

        inserted, updated = upsert_staging(cursor)

        assert (inserted, updated) == (2, 1)
        sql = cursor.executed[0][0]
        assert "INSERT INTO warehouse.cleaned_online_retail_ii" in sql
        assert "ON CONFLICT (source_row_id) DO UPDATE" in sql
        assert "loaded_at = NOW()" in sql
        assert "line_total = EXCLUDED.line_total" in sql
        assert "RETURNING (xmax = 0) AS inserted" in sql
        insert_columns = sql.split("INSERT INTO", 1)[1].split("SELECT", 1)[0]
        assert "loaded_at" not in insert_columns

    def test_upsert_with_no_returned_rows_is_zero(self):
        cursor = FakeCursor([("ON CONFLICT (source_row_id) DO UPDATE", None)])

        assert upsert_staging(cursor) == (0, 0)


class TestCounts:
    def test_count_staging_rows(self):
        cursor = FakeCursor([("SELECT COUNT(*) FROM staging_cleaned_retail", (4,))])

        assert count_staging_rows(cursor) == 4

    def test_count_table_rows(self):
        cursor = FakeCursor([("SELECT COUNT(*) FROM warehouse.cleaned_online_retail_ii", (9,))])

        assert count_table_rows(cursor) == 9


# ---------------------------------------------------------------------------
# 4. Duplicate source IDs
# ---------------------------------------------------------------------------


class TestDuplicateIds:
    def test_find_duplicates_returns_ids(self):
        cursor = FakeCursor([("GROUP BY source_row_id", [(5,), (7,)])])

        assert find_duplicate_source_row_ids(cursor) == [5, 7]

    def test_run_load_fails_and_rolls_back_on_duplicates(self, tmp_path):
        input_path = tmp_path / "data.csv"
        report_path = tmp_path / "report.json"
        _write_csv(
            input_path,
            [_row(source_row_id="1"), _row(source_row_id="1", invoice="INV-2")],
        )
        cursor = FakeCursor(_responses(staged=2, duplicates=[(1,)]))
        factory = FakeFactory(cursor)

        with pytest.raises(LoaderError, match="Duplicate"):
            run_load(
                input_path,
                report_path,
                dsn="postgresql://test",
                connection_factory=factory,
            )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "failed"
        assert report["duplicate_source_row_ids"] == [1]
        assert factory.connection.rolled_back is True
        assert factory.connection.committed is False
        assert not any("ON CONFLICT" in sql for sql, _ in cursor.executed)


# ---------------------------------------------------------------------------
# 5. End-to-end orchestration
# ---------------------------------------------------------------------------


class TestRunLoad:
    def test_success_report_and_commit(self, tmp_path):
        input_path = tmp_path / "data.csv"
        report_path = tmp_path / "report.json"
        _write_csv(
            input_path,
            [
                _row(source_row_id="1"),
                _row(source_row_id="2", invoice="INV-2"),
                _row(source_row_id="3", invoice="INV-3"),
            ],
        )
        cursor = FakeCursor(_responses(staged=3, upsert=(2, 1), final=10))
        factory = FakeFactory(cursor)

        report = run_load(
            input_path,
            report_path,
            dsn="postgresql://test",
            connection_factory=factory,
        )

        assert report["status"] == "success"
        assert report["input_rows"] == 3
        assert report["staged_rows"] == 3
        assert report["inserted_rows"] == 2
        assert report["updated_rows"] == 1
        assert report["final_rows"] == 10
        assert report["row_count_matches"] is True
        assert report["duration_seconds"] >= 0
        assert factory.connection.committed is True
        assert factory.connection.rolled_back is False
        assert len(cursor.copies) == 1

        loaded = json.loads(report_path.read_text(encoding="utf-8"))
        assert loaded["status"] == "success"
        assert loaded["input_rows"] == 3
        assert loaded["inserted_rows"] == 2
        assert loaded["updated_rows"] == 1
        assert loaded["final_rows"] == 10

    def test_empty_input_writes_empty_report_without_upsert(self, tmp_path):
        input_path = tmp_path / "data.csv"
        report_path = tmp_path / "report.json"
        _write_csv(input_path, [])
        cursor = FakeCursor(_responses(staged=0, final=5))
        factory = FakeFactory(cursor)

        report = run_load(
            input_path,
            report_path,
            dsn="postgresql://test",
            connection_factory=factory,
        )

        assert report["status"] == "empty"
        assert report["input_rows"] == 0
        assert report["staged_rows"] == 0
        assert report["inserted_rows"] == 0
        assert report["updated_rows"] == 0
        assert report["final_rows"] == 5
        assert factory.connection.committed is True
        assert not any("ON CONFLICT" in sql for sql, _ in cursor.executed)
        assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "empty"

    def test_repeated_execution_upserts_instead_of_inserting(self, tmp_path):
        input_path = tmp_path / "data.csv"
        _write_csv(
            input_path,
            [_row(source_row_id="1"), _row(source_row_id="2", invoice="INV-2")],
        )

        first_cursor = FakeCursor(_responses(staged=2, upsert=(2, 0), final=2))
        first_factory = FakeFactory(first_cursor)
        first = run_load(
            input_path,
            tmp_path / "first.json",
            dsn="postgresql://test",
            connection_factory=first_factory,
        )

        second_cursor = FakeCursor(_responses(staged=2, upsert=(0, 2), final=2))
        second_factory = FakeFactory(second_cursor)
        second = run_load(
            input_path,
            tmp_path / "second.json",
            dsn="postgresql://test",
            connection_factory=second_factory,
        )

        assert first["inserted_rows"] == 2
        assert first["updated_rows"] == 0
        assert second["inserted_rows"] == 0
        assert second["updated_rows"] == 2
        assert second["final_rows"] == 2
        assert first_factory.connection.committed is True
        assert second_factory.connection.committed is True


# ---------------------------------------------------------------------------
# 6. Rollback and failure reporting
# ---------------------------------------------------------------------------


class TestRollback:
    def test_upsert_failure_rolls_back_and_writes_failed_report(self, tmp_path):
        input_path = tmp_path / "data.csv"
        report_path = tmp_path / "report.json"
        _write_csv(input_path, [_row()])

        def _fail() -> tuple[int, int]:
            raise RuntimeError("upsert failed")

        cursor = FakeCursor(_responses(staged=1, upsert=_fail))
        factory = FakeFactory(cursor)

        with pytest.raises(RuntimeError, match="upsert failed"):
            run_load(
                input_path,
                report_path,
                dsn="postgresql://test",
                connection_factory=factory,
            )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "failed"
        assert report["error_type"] == "RuntimeError"
        assert "upsert failed" in report["error"]
        assert factory.connection.rolled_back is True
        assert factory.connection.committed is False

    def test_invalid_header_fails_before_connecting(self, tmp_path):
        input_path = tmp_path / "data.csv"
        report_path = tmp_path / "report.json"
        header = list(EXPECTED_COLUMNS)
        header[0], header[1] = header[1], header[0]
        _write_csv(input_path, [], header=header)
        factory = FakeFactory(FakeCursor())

        with pytest.raises(LoaderError, match="header"):
            run_load(
                input_path,
                report_path,
                dsn="postgresql://test",
                connection_factory=factory,
            )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "failed"
        assert factory.calls == []


# ---------------------------------------------------------------------------
# 7. Configuration, report writing, and CLI exit behaviour
# ---------------------------------------------------------------------------


class TestDsnAndReport:
    def test_get_dsn_reads_environment(self, monkeypatch):
        monkeypatch.setattr(loader, "load_dotenv", lambda *args, **kwargs: None)
        monkeypatch.setenv("DATABASE_URL", "postgresql://example")

        assert get_dsn() == "postgresql://example"

    def test_get_dsn_raises_when_missing(self, monkeypatch):
        monkeypatch.setattr(loader, "load_dotenv", lambda *args, **kwargs: None)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(LoaderError, match="DATABASE_URL"):
            get_dsn()

    def test_write_report_creates_parent_directory(self, tmp_path):
        path = tmp_path / "nested" / "report.json"

        write_json_report({"status": "success"}, path)

        assert json.loads(path.read_text(encoding="utf-8")) == {"status": "success"}


class TestMain:
    def test_main_exits_nonzero_on_failure(self, monkeypatch):
        def _fail() -> dict:
            raise RuntimeError("boom")

        monkeypatch.setattr(loader, "run_load", _fail)

        with pytest.raises(SystemExit) as exc_info:
            loader.main()

        assert exc_info.value.code == 1
