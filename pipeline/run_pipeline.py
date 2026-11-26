"""One-shot runner for the Online Retail II data pipeline.

This module contains orchestration only. Each stage delegates to the existing
script entry points under ``pipeline/scripts`` and stops on the first failure.
"""

from __future__ import annotations

import sys

from pipeline.scripts import cleaner, data_quality, loader, profiler, transformer


def main() -> int:
    """Run profile, clean, transform, validate, and load in order."""
    print("=== profile ===", flush=True)
    profiler.main()

    print("=== clean ===", flush=True)
    cleaner.run_cleaning()

    print("=== transform ===", flush=True)
    transformer.run_transformation()

    print("=== data_quality ===", flush=True)
    quality_report = data_quality.run_validation()
    if quality_report.get("status") != "passed":
        summary = quality_report.get("summary", {})
        print(
            "Data quality validation failed; refusing to load: "
            f"status={quality_report.get('status')} "
            f"failed_checks={summary.get('failed_checks')} "
            f"rows_with_any_failure={summary.get('rows_with_any_failure')}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print("=== load ===", flush=True)
    try:
        load_report = loader.run_load()
    except Exception as exc:
        print(
            f"Load failed ({type(exc).__name__}); see "
            f"{loader.LOAD_REPORT_PATH} for sanitized details.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    if load_report.get("status") not in {"success", "empty"}:
        print(
            f"Load did not succeed: status={load_report.get('status')}",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print(
        "Load complete: "
        f"status={load_report.get('status')} "
        f"input={load_report.get('input_rows')} "
        f"staged={load_report.get('staged_rows')} "
        f"inserted={load_report.get('inserted_rows')} "
        f"updated={load_report.get('updated_rows')} "
        f"final={load_report.get('final_rows')}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
