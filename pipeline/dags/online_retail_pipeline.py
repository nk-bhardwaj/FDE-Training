"""Airflow DAG for the Online Retail II data engineering pipeline.

The DAG orchestrates the existing pipeline scripts without reimplementing any
processing logic:

1. ``profiler.py`` profiles the raw CSV.
2. ``cleaner.py`` cleans and quarantines raw records.
3. ``transformer.py`` produces the warehouse-shaped transformed CSV.
4. ``data_quality.py`` validates the transformed data.
5. ``loader.py`` upserts validated rows into the Neon warehouse.

The scripts use fixed paths under ``/opt/airflow/project/pipeline/data`` and
derive their repository root from ``__file__``. The project root is mounted at
``/opt/airflow/project`` and is also on ``PYTHONPATH`` in the Airflow image.
``loader.py`` continues to read ``DATABASE_URL`` from the project root ``.env``
at runtime; no credentials are defined in this DAG.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG

DAG_ID = "online_retail_pipeline"

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}


def _run_profiler() -> None:
    """Profile the raw dataset with the existing profiler entry point."""
    from pipeline.scripts import profiler

    profiler.main()


def _run_cleaner() -> None:
    """Clean and quarantine raw records with the existing cleaner."""
    from pipeline.scripts import cleaner

    cleaner.run_cleaning()


def _run_transformer() -> None:
    """Transform cleaned records into the warehouse schema."""
    from pipeline.scripts import transformer

    transformer.run_transformation()


def _run_data_quality() -> dict[str, object]:
    """Validate transformed data and fail unless the quality report passes."""
    from pipeline.scripts import data_quality

    report = data_quality.run_validation()
    summary = report.get("summary", {})

    if report.get("status") != "passed":
        raise AirflowException(
            "Data quality validation failed: "
            f"status={report.get('status')}, "
            f"failed_checks={summary.get('failed_checks')}, "
            f"rows_with_any_failure={summary.get('rows_with_any_failure')}"
        )

    return {
        "status": report.get("status"),
        "total_rows": report.get("total_rows"),
        "total_checks": summary.get("total_checks"),
        "failed_checks": summary.get("failed_checks"),
    }


def _run_loader() -> dict[str, object]:
    """Load validated transformed data into the Neon warehouse."""
    from pipeline.scripts import loader

    report = loader.run_load()
    return {
        "status": report.get("status"),
        "input_rows": report.get("input_rows"),
        "staged_rows": report.get("staged_rows"),
        "inserted_rows": report.get("inserted_rows"),
        "updated_rows": report.get("updated_rows"),
        "final_rows": report.get("final_rows"),
    }


with DAG(
    dag_id=DAG_ID,
    description=(
        "Profile, clean, transform, validate, and load the Online Retail II "
        "dataset into the Neon warehouse."
    ),
    doc_md=__doc__,
    start_date=datetime(2025, 1, 1, tzinfo=UTC),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["online-retail", "batch", "warehouse"],
) as dag:
    profile = PythonOperator(
        task_id="profile",
        python_callable=_run_profiler,
    )
    clean = PythonOperator(
        task_id="clean",
        python_callable=_run_cleaner,
    )
    transform = PythonOperator(
        task_id="transform",
        python_callable=_run_transformer,
    )
    data_quality = PythonOperator(
        task_id="data_quality",
        python_callable=_run_data_quality,
    )
    load = PythonOperator(
        task_id="load",
        python_callable=_run_loader,
    )

    profile >> clean >> transform >> data_quality >> load
