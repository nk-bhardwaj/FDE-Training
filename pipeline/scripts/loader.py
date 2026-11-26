"""PostgreSQL loader for the transformed Online Retail II dataset.

Reads ``pipeline/data/cleaned/online_retail_II_transformed.csv`` as a stream,
bulk-loads it into a temporary staging table with PostgreSQL ``COPY``, and
upserts the staged rows into ``warehouse.cleaned_online_retail_ii`` using
``source_row_id`` as the conflict key.

Design notes
------------
* The CSV is streamed directly from disk into ``COPY ... FROM STDIN`` and is
  never materialised as a DataFrame or a list of rows.
* ``COPY`` targets a transaction-scoped temporary table created with
  ``LIKE warehouse.cleaned_online_retail_ii``. The staging table intentionally
  has no primary key so duplicate source IDs can be detected before the upsert.
* Monetary and timestamp values are transferred as text and parsed by
  PostgreSQL, preserving ``NUMERIC`` precision, nullable fields, and
  timezone-naive timestamps.
* ``loaded_at`` is omitted from the INSERT column list so PostgreSQL applies
  its ``DEFAULT NOW()``; the ``DO UPDATE`` branch refreshes it explicitly.
* A single transaction wraps staging, COPY, and upsert. Any failure rolls the
  whole load back, and ``ON COMMIT DROP`` removes the staging table.
* No RAG tables, extensions, or existing pipeline outputs are modified.
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths (relative to __file__, not cwd)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # .../fde-ai-sprint

TRANSFORMED_CSV = REPO_ROOT / "pipeline" / "data" / "cleaned" / "online_retail_II_transformed.csv"

LOAD_REPORT_PATH = (
    REPO_ROOT / "pipeline" / "data" / "profiles" / "online_retail_II_load_report.json"
)

# ---------------------------------------------------------------------------
# Target contract (pipeline/docs/schema-design.md Sections 2-6)
# ---------------------------------------------------------------------------

TABLE = "warehouse.cleaned_online_retail_ii"
STAGING_TABLE = "staging_cleaned_retail"

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

COLUMNS_SQL = ", ".join(EXPECTED_COLUMNS)

CONNECT_TIMEOUT_SECONDS = 15
CHUNK_SIZE = 1024 * 1024
DUPLICATE_SAMPLE_LIMIT = 20

# Redact anything that looks like a connection string or password before a
# failure message is written to the report.
_DSN_PATTERN = re.compile(r"postgres(?:ql)?://[^\s\"']+")
_PASSWORD_PATTERN = re.compile(r"(?i)\b(password|pwd)\s*=\s*[^\s;]+")

CREATE_STAGING_SQL = f"""
    CREATE TEMP TABLE {STAGING_TABLE} (
        LIKE {TABLE}
        INCLUDING DEFAULTS
        EXCLUDING CONSTRAINTS
        EXCLUDING INDEXES
    ) ON COMMIT DROP
"""

COPY_SQL = f"""
    COPY {STAGING_TABLE} ({COLUMNS_SQL})
    FROM STDIN WITH (FORMAT CSV, HEADER FALSE, NULL '', ENCODING 'UTF8')
"""

COUNT_STAGING_SQL = f"SELECT COUNT(*) FROM {STAGING_TABLE}"

DUPLICATE_SQL = f"""
    SELECT source_row_id
    FROM {STAGING_TABLE}
    GROUP BY source_row_id
    HAVING COUNT(*) > 1
    ORDER BY source_row_id
    LIMIT {DUPLICATE_SAMPLE_LIMIT}
"""

UPSERT_SQL = f"""
    WITH upserted AS (
        INSERT INTO {TABLE} (
            {COLUMNS_SQL}
        )
        SELECT
            {COLUMNS_SQL}
        FROM {STAGING_TABLE}
        ON CONFLICT (source_row_id) DO UPDATE SET
            invoice = EXCLUDED.invoice,
            stock_code = EXCLUDED.stock_code,
            description = EXCLUDED.description,
            quantity = EXCLUDED.quantity,
            invoice_timestamp = EXCLUDED.invoice_timestamp,
            invoice_date = EXCLUDED.invoice_date,
            price = EXCLUDED.price,
            customer_id = EXCLUDED.customer_id,
            country = EXCLUDED.country,
            line_total = EXCLUDED.line_total,
            invoice_month = EXCLUDED.invoice_month,
            loaded_at = NOW()
        RETURNING (xmax = 0) AS inserted
    )
    SELECT
        COUNT(*) FILTER (WHERE inserted) AS inserted_rows,
        COUNT(*) FILTER (WHERE NOT inserted) AS updated_rows
    FROM upserted
"""

COUNT_TABLE_SQL = f"SELECT COUNT(*) FROM {TABLE}"


class LoaderError(RuntimeError):
    """Raised when a load cannot proceed safely."""


# ---------------------------------------------------------------------------
# CSV inspection and streaming COPY
# ---------------------------------------------------------------------------


def inspect_csv(path: Path) -> tuple[list[str], int]:
    """Validate the transformed CSV header and count data rows.

    The file is streamed with :mod:`csv`; no full-file materialisation occurs.
    Returns ``(header, data_row_count)``.
    """
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise LoaderError(f"CSV is empty: {path}") from exc

        if header != EXPECTED_COLUMNS:
            missing = [column for column in EXPECTED_COLUMNS if column not in header]
            extra = [column for column in header if column not in EXPECTED_COLUMNS]
            raise LoaderError(
                "Transformed CSV header does not match the warehouse schema: "
                f"missing={missing}, extra={extra}, "
                f"expected_order={EXPECTED_COLUMNS}, actual_order={header}"
            )

        return header, sum(1 for _ in reader)


def create_staging_table(cursor: Any) -> None:
    """Create the transaction-scoped staging table."""
    cursor.execute(CREATE_STAGING_SQL)


def stream_csv_to_copy(cursor: Any, path: Path) -> None:
    """Stream *path* into the staging table using PostgreSQL COPY.

    The header line is skipped (it was already validated) and the remaining
    bytes are written to the COPY stream in fixed-size chunks.
    """
    with open(path, "rb") as handle:
        handle.readline()  # discard the validated header
        with cursor.copy(COPY_SQL) as copy:
            while chunk := handle.read(CHUNK_SIZE):
                copy.write(chunk)


# ---------------------------------------------------------------------------
# Staging and upsert operations
# ---------------------------------------------------------------------------


def count_staging_rows(cursor: Any) -> int:
    """Return the number of rows copied into the staging table."""
    cursor.execute(COUNT_STAGING_SQL)
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def find_duplicate_source_row_ids(cursor: Any) -> list[int]:
    """Return a sample of duplicate ``source_row_id`` values in staging."""
    cursor.execute(DUPLICATE_SQL)
    return [int(row[0]) for row in cursor.fetchall()]


def upsert_staging(cursor: Any) -> tuple[int, int]:
    """Upsert staged rows and return ``(inserted_rows, updated_rows)``.

    ``xmax = 0`` distinguishes freshly inserted rows from rows updated by the
    ``ON CONFLICT`` branch.
    """
    cursor.execute(UPSERT_SQL)
    row = cursor.fetchone()
    if not row:
        return 0, 0
    return int(row[0]), int(row[1])


def count_table_rows(cursor: Any) -> int:
    """Return the total number of rows in the warehouse table."""
    cursor.execute(COUNT_TABLE_SQL)
    row = cursor.fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# Connection, report, and orchestration
# ---------------------------------------------------------------------------


def get_dsn() -> str:
    """Load the root ``.env`` and return ``DATABASE_URL`` without logging it."""
    load_dotenv(REPO_ROOT / ".env")
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise LoaderError("DATABASE_URL is not configured")
    return dsn


def write_json_report(report: dict[str, Any], path: Path) -> None:
    """Write the load report, creating its parent directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)


def _sanitize_error(exc: BaseException) -> str:
    """Return an error message with connection strings and passwords redacted."""
    message = _DSN_PATTERN.sub("postgresql://***", str(exc))
    return _PASSWORD_PATTERN.sub(r"\1=***", message)


def run_load(
    input_path: Path | str | None = None,
    report_path: Path | str | None = None,
    *,
    dsn: str | None = None,
    connection_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Stream, stage, and upsert the transformed CSV.

    Returns the JSON-serialisable load report. The report is written even when
    the load fails, and the exception is re-raised so callers can exit non-zero.
    """
    input_file = Path(input_path) if input_path is not None else TRANSFORMED_CSV
    report_file = Path(report_path) if report_path is not None else LOAD_REPORT_PATH
    started = time.perf_counter()

    report: dict[str, Any] = {
        "report_version": "1.0",
        "started_at": datetime.now(UTC).isoformat(),
        "finished_at": None,
        "input_path": str(input_file),
        "report_path": str(report_file),
        "table": TABLE,
        "input_rows": 0,
        "staged_rows": 0,
        "inserted_rows": 0,
        "updated_rows": 0,
        "final_rows": 0,
        "duration_seconds": 0.0,
        "status": "failed",
    }

    try:
        _, input_rows = inspect_csv(input_file)
        report["input_rows"] = input_rows

        resolved_dsn = dsn or get_dsn()
        factory = connection_factory or psycopg.connect

        with (
            factory(resolved_dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS) as conn,
            conn.cursor() as cursor,
        ):
            create_staging_table(cursor)
            stream_csv_to_copy(cursor, input_file)

            staged_rows = count_staging_rows(cursor)
            report["staged_rows"] = staged_rows
            report["row_count_matches"] = input_rows == staged_rows

            duplicates = find_duplicate_source_row_ids(cursor)
            if duplicates:
                report["duplicate_source_row_ids"] = duplicates
                raise LoaderError(f"Duplicate source_row_id values found in staging: {duplicates}")

            if staged_rows:
                inserted_rows, updated_rows = upsert_staging(cursor)
            else:
                inserted_rows, updated_rows = 0, 0

            report["inserted_rows"] = inserted_rows
            report["updated_rows"] = updated_rows
            report["final_rows"] = count_table_rows(cursor)
            report["status"] = "empty" if staged_rows == 0 else "success"
    except Exception as exc:
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
        report["error"] = _sanitize_error(exc)
        raise
    finally:
        report["duration_seconds"] = round(time.perf_counter() - started, 3)
        report["finished_at"] = datetime.now(UTC).isoformat()
        write_json_report(report, report_file)

    return report


def main() -> None:
    """Run the load and exit non-zero if it fails."""
    try:
        report = run_load()
    except Exception as exc:
        print(f"Load failed: {_sanitize_error(exc)}")
        raise SystemExit(1) from exc

    print(f"Load report written to {report['report_path']}")
    print(
        f"Status: {report['status']} | input={report['input_rows']} | "
        f"staged={report['staged_rows']} | inserted={report['inserted_rows']} | "
        f"updated={report['updated_rows']} | final={report['final_rows']} | "
        f"duration={report['duration_seconds']}s"
    )


if __name__ == "__main__":
    main()
