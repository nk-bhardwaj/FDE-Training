# FDE AI Sprint — Data Engineering Design Document

**Project:** Clean the Online Retail II dataset and prepare structured output for RAG  
**Branch:** `feat/data-engineering-pipeline`  
**Status:** Design phase — not yet implemented  

---

## 1. Overview

This document describes the end-to-end data engineering pipeline for the **Online Retail II** dataset. The pipeline ingests the raw CSV, profiles data quality, applies documented cleaning rules, validates the cleaned output, loads it into a dedicated PostgreSQL warehouse schema (separate from the existing Week 1 RAG database), and prepares a documented output contract that Jahnvi's RAG system can consume later.

---

## 2. Objectives

| Objective | Description |
|---|---|
| **Ingest** | Read the raw CSV in a streaming / chunked fashion to avoid memory pressure. |
| **Profile** | Compute and persist per-column statistics (null counts, distinct counts, min/max, value distributions) for auditability. |
| **Clean** | Apply explicit, deterministic rules to handle missing values, duplicates, and invalid numeric ranges. |
| **Transform** | Normalize types, derive useful fields (e.g., line total, date parts), and produce a tidy schema. |
| **Validate** | Enforce row-level and dataset-level checks; distinguish warnings, quarantined records, and hard validation failures. |
| **Rejection handling** | Write rejected rows to `pipeline/data/rejected/` and quarantined rows to `pipeline/data/quarantined/`, partitioned by rule/failure type. |
| **PostgreSQL load** | Load the cleaned dataset into a dedicated warehouse schema in Neon PostgreSQL, separate from the RAG schema. |
| **RAG preparation** | Produce a documented output contract (schema, formats, metadata fields) that Jahnvi's RAG system can consume later. No direct load into the existing RAG `documents` table. |

---

## 3. Source Dataset

| Property | Value |
|---|---|
| **File path** | `pipeline/data/raw/online_retail_II.csv` |
| **Format** | CSV with header |
| **Size** | ~94 MB (94,850,204 bytes) |
| **Rows** | 1,067,371 |
| **Columns** | 8 |
| **Header** | `Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country` |

### 3.1 Known Quality Issues (from initial profiling)

| Issue | Count | Notes |
|---|---:|---|
| Missing `Description` | 4,382 | Missing per initial profiling |
| Missing `Customer ID` | 243,007 | Missing per initial profiling |
| Excess duplicate rows | 34,335 | Exact row duplicates beyond first occurrence |
| Duplicate groups | 32,907 | Distinct groups of duplicated rows |
| Negative `Quantity` | 22,950 | May represent returns or cancellations |
| Zero `Price` | 6,202 | Could be legitimate free items or data errors — policy decision required |
| Negative `Price` | 5 | Quarantine for investigation |

---

## 4. Architecture

### 4.1 High-Level Data Flow

```
┌──────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────────┐
│  pipeline/data/  │     │   Profiling  │     │  Cleaning   │     │ Transformation │
│     raw/         │────▶│  (statistics)│────▶│  (rules)    │────▶│ (normalization)│
│ online_retail_II.csv│   │              │     │             │     │                │
└──────────────────┘     └──────────────┘     └─────────────┘     └───────┬────────┘
                                                                           │
              ┌───────────────────┐     ┌──────────────┐            │
              │     Quarantined   │     │  Validation  │◀───────────┘
              │ pipeline/data/   │     │  (gates)     │
              │   quarantined/   │     │              │
              └───────────────────┘     └──────┬───────┘
                                             │
              ┌───────────────────┐     ┌─────▼────────┐
              │      Rejected     │     │     RAG Prep │
              │ pipeline/data/   │     │ (output     │
              │   rejected/      │◀────│  contract)   │
              └───────────────────┘     └──────┬──────┘
                                             │
                                             ▼
                                      ┌──────────────┐
                                      │  PostgreSQL  │
                                      │   Load       │
                                      └──────────────┘
```

### 4.2 Stage Definitions

| Stage | Input | Output | Responsibility |
|---|---|---|---|
| **Ingestion** | `pipeline/data/raw/online_retail_II.csv` | Pandas DataFrame (chunked) / Arrow table | Read-only streaming read; no writes. |
| **Profiling** | Ingestion output | `pipeline/data/profiles/online_retail_II_profile.json` | Column stats: dtype, null count, distinct count, min/max, top-k values, duplicate count. |
| **Cleaning** | Ingestion output + profile | Cleaned DataFrame + Quarantined DataFrame + Rejected DataFrame | Apply deterministic rules; emit quarantined rows with `rejection_reason` and `rejection_stage="cleaning"`. |
| **Transformation** | Cleaned DataFrame | Transformed DataFrame | Type casting, derived columns (`LineTotal = Quantity * Price`), date parsing (`InvoiceDate` → `InvoiceTimestamp`, `InvoiceDateOnly`), string trimming. |
| **Validation** | Transformed DataFrame | Validated DataFrame + Rejected DataFrame | Row-level checks (required identifiers, data types, date parsing, etc.). Failures → `rejected/` with `rejection_stage="validation"`. |
| **Rejection handling** | Rejected DataFrames (cleaning + validation) | `pipeline/data/rejected/YYYYMMDD_HHMMSS/` (partitioned CSV/Parquet) | Consolidate all rejections; include original row + `rejection_reason` + `rejection_stage`. |
| **PostgreSQL load** | Validated DataFrame | `warehouse.cleaned_online_retail_ii` table (Neon) | Upsert by `source_row_id`; create indexes (`Invoice`, `Customer ID`, `InvoiceTimestamp`). |
| **RAG preparation** | Validated DataFrame | Documented output contract (schema, formats, metadata fields) | Define the structure Jahnvi's RAG system will consume. No direct load into the existing RAG `documents` table. |

---

## 5. Orchestration — Apache Airflow

**Airflow is the orchestrator only.** It schedules DAGs, triggers tasks, manages retries, and provides observability. **Airflow does not contain data-cleaning logic.**

### 5.1 DAG Structure

| DAG / Task | Operator | Description |
|---|---|---|
| `ingest_raw` | `PythonOperator` | Stream-read raw CSV; write intermediate files to a shared location; pass only file paths, row counts, and small metadata through XCom. |
| `profile_data` | `PythonOperator` | Compute profile JSON; persist to `pipeline/data/profiles/`. |
| `clean_data` | `PythonOperator` | Apply cleaning rules; output cleaned + quarantined + rejected DataFrames. |
| `transform_data` | `PythonOperator` | Type normalization, derived fields. |
| `validate_data` | `PythonOperator` | Run validation gates; produce validated + rejected. |
| `handle_rejections` | `PythonOperator` | Consolidate rejected outputs; write partitioned files to `pipeline/data/rejected/`. |
| `load_postgres` | `PythonOperator` | Upsert validated data into Neon `warehouse.cleaned_online_retail_ii`. |
| `prepare_rag_contract` | `PythonOperator` | Produce the documented output contract for Jahnvi's RAG system. |

### 5.2 Airflow Configuration Notes

- **Executor:** `LocalExecutor` (dev) / `CeleryExecutor` (prod) left to deployment.
- **Concurrency:** Sequential by default (each task waits for upstream). Parallelism only where stages are independent (e.g., profiling can run while ingestion streams).
- **Retries:** 1–2 with exponential backoff for transient DB/network errors.
- **XCom / Data passing:** Never pass a Pandas DataFrame or chunk iterator through XCom. Ingestion should write intermediate files to a shared location. Airflow tasks should pass only file paths, row counts, and small metadata through XCom.
- **Idempotency:** Each task must be re-runnable. Use `source_row_id` as the single primary key for upserts.

---

## 6. Data Preservation — Raw Dataset Immutability

- The file `pipeline/data/raw/online_retail_II.csv` is **read-only** for the pipeline.
- A SHA-256 checksum of the raw file is recorded at pipeline start (`pipeline/data/raw/online_retail_II.csv.sha256`).
- Post-run, the checksum is verified to ensure no accidental modification.
- All intermediate artifacts (profiles, cleaned, rejected, transformed) are written **outside** `raw/`.

---

## 7. Cleaning Rules (Deterministic, Documented)

| Rule ID | Condition | Action | Rejection Reason |
|---|---|---|---|
| `CLN-01` | `Quantity < 0` | Preserve row; classify as potential return/cancellation | — (not rejected) |
| `CLN-02` | `Price < 0` | Quarantine row for investigation | `negative_price` |
| `CLN-03` | `Price == 0` | Preserve row; flag for policy decision | — (not rejected) |
| `CLN-04` | Exact duplicate row (all 8 columns identical) beyond first occurrence | Report and investigate; do not auto-delete until business meaning is understood | — (not rejected) |
| `CLN-05` | `Description` is null/empty | Keep row; keep `Description` nullable; trim whitespace only | — (not rejected) |
| `CLN-06` | `Customer ID` is null/empty | Keep row; keep `Customer ID` nullable; do not substitute artificial values | — (not rejected) |

> **Policy decisions required:** Zero-price handling (Rule `CLN-03`), negative-price quarantine resolution (Rule `CLN-02`), and duplicate-row business meaning (Rule `CLN-04`). These should be agreed with the product owner before implementation.

---

## 8. Transformation Details

| Operation | Specification |
|---|---|
| `source_row_id` | Generated from the original CSV data-row position, starting at 1 after the header. Stable across chunked ingestion and all downstream stages (cleaning, transformation, validation, rejection). |
| `Invoice` | Strip whitespace; store as TEXT (may contain alpha prefixes). |
| `StockCode` | Strip whitespace; store as TEXT. |
| `Description` | Strip whitespace; keep nullable; do not invent descriptions. |
| `Quantity` | Cast to `Int64` (integer; no missing values permitted). Preserve negative values as returns/cancellations. |
| `Price` | Cast to `NUMERIC` (monetary; no missing values in the initial profile). |
| `InvoiceDate` | Inspect the source format (the initial sample contains dates such as `2009-12-01 07:45:00`) and validate the parsed result. Parse to `InvoiceTimestamp` (timestamp without timezone) + `InvoiceDateOnly` (date). Preserve the original timestamp without assuming a timezone. |
| `Customer ID` | Strip whitespace; store as TEXT; keep nullable. |
| `Country` | Strip whitespace; preserve source country names; do not assume ISO codes. |
| **Derived** | `LineTotal = Quantity * Price` (NUMERIC). |
| **Derived** | `InvoiceMonth = InvoiceTimestamp.dt.to_period('M')` for partitioning. |

---

## 9. Validation Gates

| Gate ID | Check | Failure Action |
|---|---|---|
| `VAL-01` | `Invoice` not null | Reject row (`missing_invoice`) |
| `VAL-02` | `StockCode` not null | Reject row (`missing_stockcode`) |
| `VAL-03` | `Quantity` is present and a valid integer (no missing values in initial profile) | Reject row (`missing_or_invalid_quantity`) |
| `VAL-04` | `Price` is present and a valid numeric (no missing values in initial profile) | Reject row (`missing_or_invalid_price`) |
| `VAL-05` | `InvoiceTimestamp` parsed successfully | Reject row (`invalid_invoice_date`) |
| `VAL-06` | `source_row_id` present, positive, and unique across the dataset | Reject row (`missing_or_duplicate_source_row_id`) |
| `VAL-07` | `Country` in observed source values | Warn only; keep row |

> **Warning vs. quarantine vs. hard failure:** Warnings are logged but the row is kept. Quarantined rows (e.g., negative price) are written to `pipeline/data/quarantined/` for investigation but excluded from the validated set. Hard failures are written to `pipeline/data/rejected/` with a reason code.

---

## 10. Rejection Handling

- All rejected rows from cleaning and validation are combined into a single DataFrame with columns: original 8 fields + `source_row_id` + `rejection_reason` + `rejection_stage` + `rejection_timestamp`.
- Written to `pipeline/data/rejected/YYYYMMDD_HHMMSS_rejected.parquet` (partitioned by run timestamp).
- Quarantined rows are written separately to `pipeline/data/quarantined/YYYYMMDD_HHMMSS_quarantined.parquet`.
- A summary CSV `pipeline/data/rejected/YYYYMMDD_HHMMSS_summary.csv` is also produced with counts per `rejection_reason` and `rejection_stage`.

---

## 11. PostgreSQL Load

**Target schema:** `warehouse` (separate from the existing Week 1 RAG schema).  
**Target table:** `warehouse.cleaned_online_retail_ii`

```sql
CREATE SCHEMA IF NOT EXISTS warehouse;

CREATE TABLE IF NOT EXISTS warehouse.cleaned_online_retail_ii (
    source_row_id       BIGINT PRIMARY KEY,
    invoice             TEXT NOT NULL,
    stock_code          TEXT NOT NULL,
    description         TEXT,
    quantity            BIGINT NOT NULL,
    invoice_timestamp   TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    invoice_date        DATE NOT NULL,
    price               NUMERIC(12, 4) NOT NULL,
    customer_id         TEXT,
    country             TEXT NOT NULL,
    line_total          NUMERIC(14, 4) NOT NULL,
    invoice_month       TEXT NOT NULL,          -- e.g., '2023-01'
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cleaned_retail_customer_id
    ON warehouse.cleaned_online_retail_ii (customer_id);

CREATE INDEX IF NOT EXISTS idx_cleaned_retail_invoice_ts
    ON warehouse.cleaned_online_retail_ii (invoice_timestamp);

CREATE INDEX IF NOT EXISTS idx_cleaned_retail_country
    ON warehouse.cleaned_online_retail_ii (country);
```

- Load via `COPY` (batch) or `executemany` with `ON CONFLICT (source_row_id) DO UPDATE`.
- Transaction per batch; commit after each batch.
- The warehouse schema is **separate** from the existing RAG database/schema. No direct load into the RAG `documents` table.

---

## 12. RAG Preparation

The existing RAG system (FastAPI + Neon + pgvector + `gemini-embedding-001`) expects documents in the `documents` table with `content`, `embedding` (VECTOR(768)), and `metadata` (JSONB).

**For now, RAG preparation produces a documented output contract only.** No direct load into the existing RAG `documents` table. The existing RAG services and database schema are **not** modified.

### 12.1 Output Contract

| Field | Type | Description |
|---|---|---|
| `source_id` | `string` | Always `"online_retail_ii"` |
| `category` | `string` | `"transaction"` |
| `invoice_id` | `string` | Source `Invoice` |
| `customer_id` | `string \| null` | Source `Customer ID` (nullable) |
| `country` | `string` | Source `Country` |
| `invoice_date` | `string (ISO 8601)` | `InvoiceDateOnly` |
| `line_count` | `integer` | Number of lines in the invoice |
| `invoice_total` | `decimal` | Sum of `LineTotal` for the invoice |
| `content` | `string` | Human-readable invoice summary |

### 12.2 Document Construction Strategy

**Option A (invoice-level — recommended for RAG):**
- One document per unique `Invoice`.
- Content = concatenated lines: `"Invoice INV12345 (Customer C123, UK) — Lines: [StockCode: DESC, Qty: N, Price: £X.XX, Total: £Y.YY]; ..."`

**Option B (line-level):**
- One document per invoice line (row).
- Higher granularity but more chunks; may exceed context window for large invoices.

> **Decision:** Start with Option A. Evaluate retrieval quality; if granularity is insufficient, add Option B as supplementary chunks.

### 12.3 Future Integration

When Jahnvi's RAG system is ready to consume the output, the contract above defines the required fields. The RAG team can then decide whether to:
- Load directly into the existing `documents` table, or
- Create a new table/schema for retail transactions.

This decision is **out of scope** for the current design phase.

---

## 13. Success Metrics (Measurable)

| Metric | Target / Measurement Method | Status |
|---|---|---|
| **Raw file integrity** | SHA-256 pre-run == post-run | ⬜ Pending run |
| **Row retention rate** | `(validated_rows / 1,067,371) * 100%` — measured after execution | ⬜ Pending run |
| **Duplicate reporting** | `duplicate_row` count reported; policy decision documented | ⬜ Pending run |
| **Negative quantity classification** | `negative_quantity` count reported; classified as returns/cancellations | ⬜ Pending run |
| **Negative price quarantine** | `negative_price` count == 5 (per profile) | ⬜ Pending run |
| **Zero price handling** | `zero_price` count reported; policy decision documented | ⬜ Pending run |
| **Missing description** | Rows with `Description IS NULL` == 4,382 (per profile) | ⬜ Pending run |
| **Missing customer ID** | Rows with `Customer ID IS NULL` == 243,007 (per profile) | ⬜ Pending run |
| **PostgreSQL load completeness** | `SELECT COUNT(*) FROM warehouse.cleaned_online_retail_ii` == validated_rows | ⬜ Pending run |
| **RAG output contract** | Documented contract produced and reviewed by Jahnvi's team | ⬜ Pending review |
| **End-to-end latency** | Pipeline wall-clock time — record actual execution time first | ⬜ Pending run |

> **Important:** The "Pending run" metrics above are **measurable targets**, not measured results. Actual values will be recorded only after a successful pipeline execution. Do not populate these with fabricated numbers.

---

## 14. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Raw file accidentally overwritten** | Low | High (data loss) | Checksum verification pre/post; OS-level read-only flag on `raw/` dir in CI. |
| **Memory pressure on 94 MB CSV** | Medium | Medium | Stream in chunks (Pandas `chunksize` / PyArrow); write intermediates to Parquet. |
| **Airflow XCom overflow** | Medium | High (task failure) | Never pass DataFrames via XCom; use shared volume `/tmp/pipeline/` for Parquet hand-off. |
| **Schema drift in source CSV** | Low | High | Profile step validates expected columns; fail fast on mismatch. |
| **Zero-price policy ambiguity** | High | Medium | Default to preserve and flag; expose as DAG param `zero_price_policy` (`preserve` \| `reject`); document decision. |
| **Negative quantity misinterpretation** | Medium | Medium | Preserve as returns/cancellations; document classification logic. |
| **Large invoices exceed chunk context** | Medium | Medium | Option A (invoice-level) keeps document count manageable; if single invoice > chunk budget, split by line groups. |
| **Neon connection / pgvector errors** | Low | High | Retries with backoff; dead-letter failed batches to `rejected/` for manual review. |
| **Embedding API rate limits (Gemini)** | Medium | Medium | Batch embed requests; respect `EmbeddingService` internal rate limiting; configurable concurrency. |
| **Date parsing errors (mixed formats)** | Low | Medium | Inspect the source date format, parse and validate timestamps, and route unparseable values to rejection with `invalid_invoice_date`. |

---

## 15. Out of Scope / Constraints

- **No changes to the main FastAPI app (`app/`)** — RAG preparation uses existing services as libraries.
- **No new dependencies** beyond what `pyproject.toml` already declares (`pandas`, `psycopg`, `pgvector`, `google-genai`, etc.).
- **No modification of `pyproject.toml`, `uv.lock`, or any file outside `pipeline/docs/design-document.md`.**
- **No fabricated statistics** — all figures in this document are sourced from the initial profile provided in Section 3.1 or derived deterministically from them.
- **No live execution results** — this is a design document. Measured results will be appended in a separate run-report document after execution.

---

## 16. Appendix — Dataset Schema Snapshot

| Column | Pandas dtype | PostgreSQL type | Nullable | Notes |
|---|---|---|---|---|
| `source_row_id` | `int64` | `BIGINT` | No | Primary key; CSV row position (1-based after header) |
| `Invoice` | `string` | `TEXT` | No | May contain alpha prefixes |
| `StockCode` | `string` | `TEXT` | No | |
| `Description` | `string` | `TEXT` | Yes | Kept nullable; trimmed only |
| `Quantity` | `Int64` | `BIGINT` | No | Negative values preserved as returns/cancellations; no missing values in initial profile |
| `InvoiceDate` | `string` (raw) | — | — | Parsed to `InvoiceTimestamp` / `InvoiceDateOnly` |
| `Price` | `Float64` | `NUMERIC(12, 4)` | No | Zero and negative values handled per policy |
| `Customer ID` | `string` | `TEXT` | Yes | Kept nullable; no artificial substitution |
| `Country` | `string` | `TEXT` | No | Preserved as source country names |

---

*End of design document.*