# FDE AI Sprint — Schema Design Document

**Project:** Clean the Online Retail II dataset and prepare structured output for RAG  
**Source of truth:** `pipeline/docs/design-document.md`  
**Branch:** `feat/data-engineering-pipeline`  
**Status:** Design phase — not yet implemented  

---

## 1. Purpose and Scope of the Warehouse Schema

The `warehouse.cleaned_online_retail_ii` table is a dedicated PostgreSQL warehouse schema **separate from the existing Week 1 RAG database/schema**. Its purpose is to store the cleaned, transformed, and validated rows from the Online Retail II dataset (`pipeline/data/raw/online_retail_II.csv`) with a stable source-row identifier (`source_row_id`) and monetary precision appropriate for financial analysis.

**Key principles:**

- The warehouse schema is read-only for downstream consumers during normal operations; upserts use `ON CONFLICT (source_row_id)`.
- No direct load into the existing RAG `documents` table. RAG preparation consumes a documented output contract (see §14).
- The original raw CSV at `pipeline/data/raw/online_retail_II.csv` is never modified; all transformations read from it and write intermediates to `pipeline/data/cleaned/`, `pipeline/data/rejected/`, and `pipeline/data/quarantined/`.
- Negative quantities and zero prices are preserved per documented policy; they are not automatically filtered out.
- `source_row_id` is the single primary key; `Invoice + StockCode` is **not** a primary key (the combination is not guaranteed unique).

**Scope includes:**

- All 8 original CSV columns plus `source_row_id` and derived columns.
- Full data-lineage documentation from raw CSV to warehouse table.
- Index strategy for common filter patterns (customer, invoice date, country).
- Nullable columns and preservation policies for descriptions and customer IDs.
- Quarantine handling for negative-price rows.
- Idempotent loading rules using primary-key conflict resolution.

**Scope excludes:**

- Any modification to the Week 1 RAG schema (`app/` services, `documents` table, pgvector indexes).
- Automatic deletion of duplicate rows until business meaning is understood.
- Invention of row counts or rejection statistics.

---

## 2. Source-to-Target Column Mapping

| # | CSV Column | Warehouse Column | PostgreSQL Type | Nullable | Notes |
|---|---|---|---|---|---|
| 1 | `source_row_id` | `source_row_id` | `BIGINT` | No | Primary key; 1-based row position after CSV header; stable across all stages |
| 2 | `Invoice` | `invoice` | `TEXT` | No | May contain alpha prefixes; stripped of whitespace |
| 3 | `StockCode` | `stock_code` | `TEXT` | No | |
| 4 | `Description` | `description` | `TEXT` | Yes | Kept nullable; trimmed whitespace only; no invented descriptions |
| 5 | `Quantity` | `quantity` | `BIGINT` | No | Negative values preserved as returns/cancellations; no missing values in initial profile |
| 6 | `InvoiceDate` | `invoice_timestamp` | `TIMESTAMP WITHOUT TIME ZONE` | No | Parsed and validated; original timestamp preserved without timezone assumption |
| 7 | `Price` | `price` | `NUMERIC(12,4)` | No | Zero and negative values handled per policy |
| 8 | `Customer ID` | `customer_id` | `TEXT` | Yes | Kept nullable; no artificial substitution (e.g. "[UNKNOWN]") |
| 9 | `Country` | `country` | `TEXT` | No | Preserved as source country names |

**Derived columns** (not present in the original CSV; computed during transformation):

| Derived Column | Expression | Type | Nullable | Description |
|---|---|---|---|---|
| `invoice_date` | `invoice_timestamp::date` | `DATE` | No | `invoice_timestamp::date`; ISO-8601 format 'YYYY-MM-DD' |
| `line_total` | `quantity * price` | `NUMERIC(14,4)` | No | Extended price per line; preserved with monetary precision |
| `invoice_month` | `invoice_timestamp.dt.to_period('M')` → text 'YYYY-MM' | `TEXT` | No | Derived field for month-based grouping/filtering; e.g., '2023-01' |

---

## 3. PostgreSQL Table Definition

**Target schema:** `warehouse` (created with `CREATE SCHEMA IF NOT EXISTS warehouse;`)

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
    invoice_month       TEXT NOT NULL,          -- derived field for month-based grouping/filtering, e.g., '2023-01'
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Constraints summary:**

- `source_row_id` — PRIMARY KEY; enforces uniqueness and idempotent upserts.
- `invoice` — NOT NULL; every row must have an invoice identifier.
- `stock_code` — NOT NULL; every row must have a stock keeping unit.
- `description` — nullable; may be empty or omitted in the source; trimmed but not filled.
- `quantity` — BIGINT NOT NULL; negative values permitted and preserved as returns/cancellations.
- `invoice_timestamp` — TIMESTAMP WITHOUT TIME ZONE NOT NULL; parsed and validated; timezone not assumed.
- `invoice_date` — DATE NOT NULL; extracted from `invoice_timestamp`.
- `price` — NUMERIC(12,4) NOT NULL; zero and negative values permitted per policy.
- `customer_id` — nullable TEXT; no artificial values substituted.
- `country` — NOT NULL; preserved as source country names.
- `line_total` — NUMERIC(14,4) NOT NULL; `quantity * price`.
- `invoice_month` — TEXT NOT NULL; derived field for month-based grouping and filtering.
- `loaded_at` — TIMESTAMPTZ NOT NULL DEFAULT NOW(); audit timestamp.

---

## 4. Column Definitions and Constraints

| Column | Type | Nullable | Primary Key | Constraint |
|---|---|---|---|---|
| `source_row_id` | `BIGINT` | No | Yes | Unique; 1-based after CSV header; stable across stages |
| `invoice` | `TEXT` | No | — | NOT NULL |
| `stock_code` | `TEXT` | No | — | NOT NULL |
| `description` | `TEXT` | Yes | — | Trimmed only; no invention |
| `quantity` | `BIGINT` | No | — | NOT NULL; negative values preserved |
| `invoice_timestamp` | `TIMESTAMP WITHOUT TIME ZONE` | No | — | NOT NULL; parsed & validated |
| `invoice_date` | `DATE` | No | — | NOT NULL; from `invoice_timestamp::date` |
| `price` | `NUMERIC(12,4)` | No | — | NOT NULL; zero/negative preserved |
| `customer_id` | `TEXT` | Yes | — | nullable; no substitution |
| `country` | `TEXT` | No | — | NOT NULL |
| `line_total` | `NUMERIC(14,4)` | No | — | NOT NULL; `quantity * price` |
| `invoice_month` | `TEXT` | No | — | NOT NULL; derived field for month-based grouping/filtering |
| `loaded_at` | `TIMESTAMPTZ` | — | — | DEFAULT NOW(); audit |

---

## 5. Derived Columns

### 5.1 `invoice_date`

- Expression: `invoice_timestamp::date`
- Type: `DATE NOT NULL`
- Description: Calendar date extracted from the timestamp without timezone. Represents the date on which the transaction occurred, in `YYYY-MM-DD` ISO-8601 format.

### 5.2 `line_total`

- Expression: `quantity * price` (both `BIGINT` and `NUMERIC(12,4)` → result is `NUMERIC(14,4)`)
- Type: `NUMERIC(14,4) NOT NULL`
- Description: Extended price for the line item. Because both `quantity` and `price` can be negative or zero, `line_total` can likewise be negative, zero, or positive. No business rule forces `line_total > 0`.

### 5.3 `invoice_month`

- Expression: `to_char(invoice_timestamp, 'YYYY-MM')` or `invoice_timestamp.dt.to_period('M').astype(str)`
- Type: `TEXT NOT NULL`
- Description: Derived field computed from `invoice_timestamp` for grouping and filtering by month. Format: `'YYYY-MM'` (e.g., `'2023-01'`). This column does **not** mean the table is partitioned; actual table partitioning is not applied and remains a possible future optimization.

---

## 6. Index Strategy and Rationale

| Index | Columns | Type | Rationale |
|---|---|---|---|
| `idx_cleaned_retail_customer_id` | `customer_id` | BTREE | Supports filtered queries: "Show all transactions for customer X". `customer_id` is nullable; the BTREE index handles NULLs naturally. |
| `idx_cleaned_retail_invoice_ts` | `invoice_timestamp` | BTREE | Supports range queries by date: "Show all transactions in date range [A, B]". The timestamp is used in ORDER BY and WHERE clauses for temporal analysis. |
| `idx_cleaned_retail_country` | `country` | BTREE | Supports filtered queries: "Show all transactions for country Y". Country values are preserved as source names (not normalized to ISO codes). |

**No index on `source_row_id`** is needed beyond the primary-key constraint, which already creates a unique index.

---

## 7. Handling of Nullable `description` and `customer_id`

- **`description`**: The source CSV may have missing or empty `Description` values (initial profiling: 4,382 rows). The warehouse schema keeps `description` nullable (`TEXT` with no NOT NULL constraint). The pipeline trims leading/trailing whitespace but does **not** invent descriptions or fill with placeholder text. Downstream consumers (e.g., RAG) must handle NULL descriptions gracefully.

- **`customer_id`**: The source CSV may have missing `Customer ID` values (initial profiling: 243,007 rows). The warehouse schema keeps `customer_id` nullable (`TEXT` with no NOT NULL constraint). The pipeline does **not** substitute artificial values such as `"[UNKNOWN]"` or `-1`. Downstream consumers must treat NULL `customer_id` as "unknown or missing".

Both nullable columns are preserved exactly as they appear in the source (after whitespace trimming), with no policy-driven transformation.

---

## 8. Preservation of Negative Quantities and Zero Prices

- **Negative `quantity`**: Initial profiling found 22,950 rows with `Quantity < 0`. The warehouse schema defines `quantity` as `BIGINT NOT NULL` — negative values are **permitted and preserved**. These rows are classified as potential returns or cancellations; no rejection or sign-flip occurs.

- **Zero `price`**: Initial profiling found 6,202 rows with `Price == 0`. The warehouse schema defines `price` as `NUMERIC(12,4) NOT NULL` — zero values are **permitted and preserved**. These rows are flagged for policy decision; they are neither rejected nor altered.

- **Negative `price`**: Initial profiling found 5 rows with `Price < 0`. The warehouse schema defines `price` as `NUMERIC(12,4) NOT NULL` — the schema permits negatives; however, pipeline policy quarantines negative-price rows before warehouse load for investigation. These 5 rows are **excluded** from the validated warehouse set used for RAG output generation and aggregate metrics.

**Policy**: Do not automatically filter, sign-flip, or reject negative quantities or zero prices. Preserve source values as-is. Quarantine negative-price rows for investigation.

---

## 9. Negative-Price Quarantine Policy

- Rows where `Price < 0` (initial profiling: 5 rows) are **not** loaded into `warehouse.cleaned_online_retail_ii`.
- Instead, they are written to `pipeline/data/quarantined/YYYYMMDD_HHMMSS_quarantined.parquet` with all original columns plus `source_row_id` and `rejection_reason = 'negative_price'`.
- Quarantined rows are excluded from the validated set used for RAG output generation and any aggregate metrics.
- The quarantine is a holding step; a future policy decision will determine whether to (a) reject, (b) sign-flip, or (c) preserve these 5 rows in the warehouse.

**No rows are automatically deleted** from the source or warehouse until a policy is agreed. `source_row_id` ensures these rows can be traced back to the original CSV position.

---

## 10. Duplicate Handling and the Role of `source_row_id`

- **Exact duplicate rows** (all 8 original CSV columns identical) beyond the first occurrence: initial profiling found 34,335 such rows across 32,907 duplicate groups. The pipeline **reports and investigates** these duplicates; it does **not** automatically delete them until the business meaning of repeated transaction lines is understood.

- **`source_row_id`** (1-based row position after CSV header) is the **single primary key** for the warehouse table. It:
  - Guarantees uniqueness per logical row in the warehouse.
  - Enables idempotent upserts via `ON CONFLICT (source_row_id) DO UPDATE`.
  - Traces any row back to its original CSV position.
  - Is stable across chunked ingestion, cleaning, transformation, validation, and rejection handling.

- Because `source_row_id` is unique, the `Invoice + StockCode` combination is **not** used as a primary key or unique constraint, as the combination is not guaranteed unique in the source data.

---

## 11. Idempotent Loading Using `ON CONFLICT (source_row_id)`

- Load method: stage into a temporary table via `COPY`, then `INSERT INTO warehouse.cleaned_online_retail_ii ... ON CONFLICT (source_row_id) DO UPDATE` from the staging table. Alternatively, use `executemany` with `ON CONFLICT` for smaller batches.
- On conflict (a row with the same `source_row_id` already exists), the existing row is **updated** with the new values from the incoming batch.
- This makes each loading task re-runnable: re-executing the same DAG run produces the same warehouse state, assuming the source data has not changed.
- Transaction per batch; commit after each batch for atomicity.

**SQL pattern (staging table + COPY + INSERT ... ON CONFLICT):**

```sql
-- 1. Create staging table (same schema, no PK)
CREATE TEMP TABLE staging_cleaned_retail
(LIKE warehouse.cleaned_online_retail_ii
 EXCLUDING CONSTRAINTS
 EXCLUDING INDEXES);

-- 2. Bulk load into staging via COPY (fast)
COPY staging_cleaned_retail (source_row_id, invoice, stock_code, description, quantity,
    invoice_timestamp, invoice_date, price, customer_id, country, line_total, invoice_month)
FROM STDIN WITH (FORMAT CSV);

-- 3. Upsert from staging into warehouse
INSERT INTO warehouse.cleaned_online_retail_ii
    (source_row_id, invoice, stock_code, description, quantity,
     invoice_timestamp, invoice_date, price, customer_id,
     country, line_total, invoice_month, loaded_at)
SELECT source_row_id, invoice, stock_code, description, quantity,
       invoice_timestamp, invoice_date, price, customer_id,
       country, line_total, invoice_month, NOW()
FROM staging_cleaned_retail
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
    loaded_at = NOW();
```

**Alternative (smaller batches): `executemany` with `ON CONFLICT`** — same `INSERT ... ON CONFLICT` pattern as above, executed per batch.

---

## 12. Example SQL Queries

### 12.1 Verify row counts

```sql
SELECT COUNT(*) AS total_rows
FROM warehouse.cleaned_online_retail_ii;
```

### 12.2 Verify NOT NULL constraints are satisfied

```sql
SELECT COUNT(*) AS violation_count
FROM warehouse.cleaned_online_retail_ii
WHERE quantity IS NULL
   OR price IS NULL
   OR invoice IS NULL
   OR stock_code IS NULL
   OR invoice_timestamp IS NULL
   OR invoice_date IS NULL
   OR line_total IS NULL
   OR invoice_month IS NULL;
```

### 12.3 Verify duplicate source IDs (should be 0)

```sql
SELECT COUNT(*) AS duplicate_source_rows
FROM (
    SELECT source_row_id, COUNT(*) AS cnt
    FROM warehouse.cleaned_online_retail_ii
    GROUP BY source_row_id
    HAVING COUNT(*) > 1
) sub;
```

### 12.4 Verify negative quantities are preserved

```sql
SELECT COUNT(*) AS negative_qty_count
FROM warehouse.cleaned_online_retail_ii
WHERE quantity < 0;
```

### 12.5 Verify zero prices are preserved

```sql
SELECT COUNT(*) AS zero_price_count
FROM warehouse.cleaned_online_retail_ii
WHERE price = 0;
```

### 12.6 Verify negative-price quarantine count

```sql
-- Count should be 5 (per initial profile) in the quarantine directory, not in the warehouse.
-- Warehouse should have 0 negative-price rows:
SELECT COUNT(*) AS neg_price_warehouse
FROM warehouse.cleaned_online_retail_ii
WHERE price < 0;
```

### 12.7 Verify nullable columns contain expected NULLs

```sql
SELECT COUNT(*) AS null_description
FROM warehouse.cleaned_online_retail_ii
WHERE description IS NULL;

SELECT COUNT(*) AS null_customer_id
FROM warehouse.cleaned_online_retail_ii
WHERE customer_id IS NULL;
```

---

## 13. Data Lineage from Raw CSV to Warehouse Table

| Stage | Input | Output | Key Transformations |
|---|---|---|---|
| **Raw CSV** | `pipeline/data/raw/online_retail_II.csv` | — | 1,067,371 rows × 8 columns; header: `Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country` |
| **Profiling** | Raw CSV | `pipeline/data/profiles/online_retail_II_profile.json` | Column stats: null counts, distinct counts, min/max, value distributions; identified 4 quality issue categories |
| **Ingestion** | Raw CSV | Pandas DataFrame (chunked) | Reads CSV; generates `source_row_id` (1-based after header); preserves all source columns |
| **Cleaning** | Ingestion output | Cleaned + Quarantined + Rejected DataFrames | CLN-01..CLN-06 rules: negative quantity preserved, negative price quarantined, zero price preserved, duplicates reported, missing Description/customer_id kept nullable |
| **Transformation** | Cleaned DataFrame | Transformed DataFrame | Type casting; `line_total = quantity * price`; `invoice_timestamp` parsing; `invoice_date = invoice_timestamp::date`; `invoice_month` derivation |
| **Validation** | Transformed DataFrame | Validated + Rejected DataFrames | VAL-01..VAL-07 gates: NOT NULL checks, valid integer/numeric, invoice timestamp parse, source_row_id uniqueness, country observed values |
| **PostgreSQL load** | Validated DataFrame | `warehouse.cleaned_online_retail_ii` | Upsert by `source_row_id`; indexes on `customer_id`, `invoice_timestamp`, `country`; `loaded_at` audit stamp |
| **RAG preparation** | Validated DataFrame | Documented output contract | Defines contract for Jahnvi's RAG system; no direct load into RAG `documents` table |

**Lineage integrity**: `source_row_id` is the thread that traces each warehouse row back to its original CSV position through every stage.

---

## 14. Future RAG Output Compatibility

The existing RAG system (FastAPI + Neon + pgvector + `gemini-embedding-001`) expects documents in the `documents` table with `content`, `embedding` (VECTOR(768)), and `metadata` (JSONB). **This warehouse schema is separate** and is **not** directly loaded into the RAG `documents` table.

**For now, RAG preparation produces a documented output contract** (see §12 of the design document) that defines the structure Jahnvi's RAG system can consume later. The contract fields map from warehouse columns:

| Warehouse Column | RAG Output Contract Field |
|---|---|
| `invoice` | `invoice_id` |
| `customer_id` | `customer_id` (nullable) |
| `country` | `country` |
| `invoice_date` | `invoice_date` (ISO 8601) |
| `line_total` | `invoice_total` (sum per invoice) |
| `description` | optionally included in `content` summary |
| `invoice_month` | not directly exposed; available for month-based grouping and filtering |

**Future integration path**: When Jahnvi's RAG system is ready, the RAG team can:
- Map warehouse rows to documents (one per invoice or per line), generate embeddings, and insert into the RAG `documents` table, **or**
- Create a new table/schema for retail transactions that the RAG system can query alongside other content.

This decision is **out of scope** for the current design phase.

---

## 15. Out of Scope / Constraints

- **No changes to the main FastAPI app (`app/`)** — RAG preparation uses existing services as libraries.
- **No new dependencies** beyond what `pyproject.toml` already declares.
- **No modification of `pyproject.toml`, `uv.lock`, or any file other than `pipeline/docs/schema-design.md`.**
- **No fabricated statistics** — all figures sourced from the initial profile in the design document or derived deterministically.
- **No live execution results** — this is a design document; measured results will be recorded after execution.
- **No Python code, migrations, or database changes yet** — the document describes the target schema; implementation follows in later phases.

---

*End of schema design document.*