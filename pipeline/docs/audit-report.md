# FDE AI Sprint — Audit Report
## Member D Data Engineering Project

**Project:** Clean the Online Retail II dataset and prepare structured output for RAG  
**File:** `pipeline/data/raw/online_retail_II.csv`  
**Report Date:** 2026-11-25  
**Purpose:** Independent audit of dataset profiling, quality findings, and recommended handling decisions prior to pipeline implementation.

---
## 1. Executive Summary

This audit documents the quality characteristics of the Online Retail II dataset (1,067,371 rows, 8 columns, ~94 MB CSV) as profiled prior to the data engineering pipeline implementation. Key findings include:

- **Missing values:** 4,382 rows with missing `Description` and 243,007 rows with missing `Customer ID`; all other columns have 0 missing values.
- **Duplicates:** 34,335 excess duplicate rows across 32,907 duplicate groups.
- **Numeric anomalies:** 22,950 rows with negative `Quantity`, 6,202 rows with zero `Price`, and 5 rows with negative `Price` (requiring quarantine).
- **Invoice prefixes:** Four distinct prefixes observed — `5` (939,382 rows), `4` (108,489 rows), `C` (19,494 rows), and `A` (6 rows).
- **Date range:** 2009-12-01 07:45:00 to 2011-12-09 12:50:00.
- **All recommendations preserve source values where policy permits, keep nullable columns nullable, and quarantine the 5 identified negative-price rows for investigation; additional rows may be quarantined if full-dataset timestamp validation identifies invalid dates.**

No Python code, database migrations, or schema changes are implemented in this document. All statistics are sourced from the initial profiling run and are reproduced verbatim.

---
## 2. Dataset Overview

| Property | Value |
|---|---|
| **File path** | `pipeline/data/raw/online_retail_II.csv` |
| **Format** | CSV with header |
| **File size** | 94,850,204 bytes |
| **Total rows** | 1,067,371 |
| **Total columns** | 8 |
| **Header** | `Invoice,StockCode,Description,Quantity,InvoiceDate,Price,Customer ID,Country` |
| **Date range** | 2009-12-01 07:45:00 to 2011-12-09 12:50:00 |
| **Columns** | `Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`, `Country` |

---
## 3. Schema and Data Types

The warehouse schema `warehouse.cleaned_online_retail_ii` (design referenced from `pipeline/docs/schema-design.md`) defines the following columns and types:

| Column | PostgreSQL Type | Nullable | Primary Key | Notes |
|---|---|---|---|---|
| `source_row_id` | `BIGINT` | No | Yes | 1-based row position after CSV header; stable across all stages |
| `invoice` | `TEXT` | No | — | NOT NULL; may contain alpha prefixes |
| `stock_code` | `TEXT` | No | — | NOT NULL |
| `description` | `TEXT` | Yes | — | Trimmed only; no invention |
| `quantity` | `BIGINT` | No | — | NOT NULL; Negative values preserved; classified as potential returns or cancellations |
| `invoice_timestamp` | `TIMESTAMP WITHOUT TIME ZONE` | No | — | Planned parsing and validation during pipeline execution; timezone not assumed |
| `invoice_date` | `DATE` | No | — | NOT NULL; `YYYY-MM-DD` ISO-8601 format |
| `price` | `NUMERIC(12,4)` | No | — | NOT NULL; PostgreSQL NUMERIC supports negative values; pipeline validation policy quarantines negative-price rows before warehouse loading |
| `customer_id` | `TEXT` | Yes | — | nullable; no artificial substitution |
| `country` | `TEXT` | No | — | NOT NULL; preserved as source country names |
| `line_total` | `NUMERIC(14,4)` | No | — | `quantity * price` |
| `invoice_month` | `TEXT` | No | — | Derived field for month-based grouping/filtering; format `'YYYY-MM'` |

**Constraints summary:** `source_row_id` is the single primary key; `Invoice + StockCode` is **not** a primary key as the combination is not guaranteed unique in source data. Negative quantities and zero prices are preserved; negative-price rows are quarantined.

---
## 4. Missing Value Analysis

| Column | Missing Count | Total Rows | Missing Rate | Handling Decision |
|---|---|---|---|---|
| `Description` | 4,382 | 1,067,371 | 0.41% | Keep nullable; trim whitespace only; do not invent descriptions |
| `Customer ID` | 243,007 | 1,067,371 | 22.76% | Keep nullable; do not substitute artificial values such as `"[UNKNOWN]"` or `-1` |
| `Invoice` | 0 | 1,067,371 | 0.00% | Preserve as TEXT; NOT NULL constraint satisfied |
| `StockCode` | 0 | 1,067,371 | 0.00% | Preserve as TEXT; NOT NULL constraint satisfied |
| `Quantity` | 0 | 1,067,371 | 0.00% | Preserve negative values; NOT NULL constraint satisfied |
| `Price` | 0 | 1,067,371 | 0.00% | Preserve zero prices; quarantine negative-price rows for investigation |
| `InvoiceDate` | 0 | 1,067,371 | 0.00% | Parse to timestamp; quarantine invalid timestamps |
| `Country` | 0 | 1,067,371 | 0.00% | Preserve as TEXT; NOT NULL constraint satisfied |

**Impact:** Downstream consumers (RAG, analytics) must handle NULL `Description` and `Customer ID` gracefully. No rows are rejected or altered for missing values; nullable columns are preserved exactly as they appear after whitespace trimming.

---
## 5. Duplicate Analysis

| Metric | Count | Details |
|---|---|---|
| **Excess duplicate rows** | 34,335 | Rows beyond the first occurrence where all 8 original CSV columns are identical |
| **Duplicate groups** | 32,907 | Distinct groups of duplicated rows; some groups may contain >1 excess row |
| **Unique rows (first occurrence)** | 1,033,036 | 1,067,371 − 34,335 |
| **Duplicate rate** | 3.22% | 34,335 / 1,067,371 |

**Handling decision:** The pipeline **reports and investigates** these duplicates; it does **not** automatically delete them until the business meaning of repeated transaction lines is understood. `source_row_id` (1-based CSV row position after header) is the single primary key and uniquely identifies each source CSV row. Because `source_row_id` is unique, the `Invoice + StockCode` combination is **not** used as a primary key or unique constraint.

---
## 6. Numeric Anomaly Analysis

| Anomaly Type | Count | Range | Policy Decision |
|---|---|---|---|
| **Negative Quantity** | 22,950 | −80,995 to −1 | Negative values preserved; classified as potential returns or cancellations. |
| **Zero Quantity** | 0 | N/A | N/A; no zero-quantity rows in initial profile |
| **Negative Price** | 5 | −53,594.36 to −11,062.06 | **Quarantine** for investigation; excluded from validated warehouse set; written to `pipeline/data/quarantined/` with `rejection_reason = 'negative_price'` |
| **Zero Price** | 6,202 | 0 | Preserve row; flag for reporting; neither rejected nor altered |

**Policy:** Do not automatically filter, sign-flip, or reject negative quantities or zero prices. Preserve source values as-is. Quarantine the 5 negative-price rows for future business decision (reject, sign-flip, or preserve).

---
## 7. Date and Format Analysis

| Aspect | Finding | Details |
|---|---|---|
| **Date range** | 2009-12-01 07:45:00 to 2011-12-09 12:50:00 | Spans ~2 years of transaction data |
| **Date format** | `YYYY-MM-DD HH:MM:SS` | Source format observed in initial sample (e.g., `2009-12-01 07:45:00`) |
| **Timezone** | No timezone assumption | `invoice_timestamp` stored as `TIMESTAMP WITHOUT TIME ZONE`; original timestamp preserved without timezone assumption |
| **Invalid timestamps** | Not yet measured | Full-dataset parse validation not yet performed; any rows that fail parsing will be quarantined with `invalid_invoice_date` |
| **Derived `invoice_date`** | `YYYY-MM-DD` | Extracted via `invoice_timestamp::date` from a successfully parsed `invoice_timestamp`; ISO-8601 format; target warehouse schema requires NOT NULL; invalid timestamps will be quarantined |

**Handling decision:** Parse dates from source format to `invoice_timestamp` (timestamp without timezone) and `invoice_date` (date). Preserve the original timestamp without assuming a timezone. Quarantine any rows where timestamp parsing fails. Full-dataset parsing and validation are planned pipeline operations and have not yet been completed.

---
## 8. Invoice Prefix Analysis

| Prefix | Count | Percentage of Dataset | Example Values |
|---|---|---|---|
| `5` | 939,382 | 87.99% | Standard numeric invoices |
| `4` | 108,489 | 10.16% | Numeric invoices — alternate range |
| `C` | 19,494 | 1.83% | Alphabetic prefix; business meaning not yet confirmed |
| `A` | 6 | 0.00% | Alphabetic prefix; business meaning not yet confirmed |

**Handling decision:** Store `Invoice` as `TEXT` to preserve prefixes exactly as they appear in the source data. Do not normalize or convert to ISO codes. Alphabetic prefixes (`C`, `A`) are kept as-is; business meaning not yet confirmed.

---
## 9. Data Quality Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Raw file accidentally overwritten** | Low | High (data loss) | **Planned safeguard:** SHA-256 checksum recording at pipeline start and post-run verification are planned safeguards, not yet implemented; the pipeline must not modify the raw source file. |
| **Memory pressure on 94 MB CSV** | Medium | Medium | Stream in chunks (Pandas `chunksize` / PyArrow); write intermediates to Parquet outside `raw/`. |
| **Schema drift in source CSV** | Low | High | Profiling step validates expected columns; fail fast on column count/dtype mismatch. |
| **Zero-price reporting** | Medium | Low | Zero-price preservation is documented policy; flag rows for reporting; document reporting outcomes in audit. |
| **Negative quantity misinterpretation** | Medium | Medium | Preserve negative quantities; classify as potential returns or cancellations; document classification logic and keep `source_row_id` for traceability. |
| **Large invoices exceed chunk context** | Medium | Medium | Invoice-level document grouping (Option A) keeps document count manageable; if single invoice > chunk budget, split by line groups. |
| **Neon connection / pgvector errors** | Low | High | **Out of scope for this phase** — current scope produces a PostgreSQL warehouse and RAG output contract; direct Neon integration is not implemented. |
| **Embedding API rate limits (Gemini)** | Medium | Medium | **Out of scope for this phase** — embedding generation is not implemented in this pipeline phase. |
| **Date parsing errors (mixed formats)** | Low | Medium | Inspect source date format, parse and validate timestamps, route unparseable values to rejection with `invalid_invoice_date`. |
| **Duplicate row handling backlog** | Medium | Medium | Report count in audit; business owner decides on deletion/retention; `source_row_id` ensures traceability. |

---
## 10. Recommended Cleaning and Handling Rules

| Rule ID | Condition | Action | Rejection Reason |
|---|---|---|---|
| `CLN-01` | `Quantity < 0` | Preserve row; classify as potential return/cancellation | — (not rejected) |
| `CLN-02` | `Price < 0` | Quarantine row for investigation | `negative_price` |
| `CLN-03` | `Price == 0` | Preserve row; flag for reporting; neither rejected nor altered | — (not rejected) |
| `CLN-04` | Exact duplicate row (all 8 columns identical) beyond first occurrence | Report and investigate; do not auto-delete until business meaning understood | — (not rejected) |
| `CLN-05` | `Description` is null/empty | Keep row; keep `Description` nullable; trim whitespace only | — (not rejected) |
| `CLN-06` | `Customer ID` is null/empty | Keep row; keep `Customer ID` nullable; do not substitute artificial values | — (not rejected) |
| `VAL-05` | `InvoiceTimestamp` parse fails | Reject row | `invalid_invoice_date` |

**Policy decisions (on record):**
- Missing `Description` and `Customer ID` values are kept nullable — no substitution.
- Negative quantities are preserved as-is; classified as potential returns or cancellations.
- Zero prices are preserved; not rejected or altered.
- The 5 negative-price rows are quarantined for investigation.
- Exact duplicate rows are reported and investigated; no automatic deletion.
- `Invoice` stored as TEXT to preserve alpha prefixes.
- Dates parsed and validated; invalid timestamps quarantined.

---
## 11. Impact on Downstream Warehouse and RAG

**Warehouse (`warehouse.cleaned_online_retail_ii`):**
- 1,067,371 source rows → validated load with `source_row_id` as primary key; final warehouse row count will be determined after all validation checks complete.
- 5 negative-price rows excluded from warehouse load; written to quarantine instead.
- 34,335 excess duplicate rows reported but not deleted; `source_row_id` ensures uniqueness.
- 4,382 rows with NULL `Description` and 243,007 rows with NULL `Customer ID` kept as-is (nullable).
- Negative quantities (22,950 rows) and zero prices (6,202 rows) preserved per policy.
- Invoice stored as TEXT; prefixes (`5`, `4`, `C`, `A`) retained.
- `invoice_date` in `YYYY-MM-DD` format; `invoice_month` in `YYYY-MM` format for grouping.

**RAG output contract (referenced from `pipeline/docs/design-document.md` §12):**
- No direct load into existing RAG `documents` table.
- Documented output contract defines structure for Jahnvi's RAG system to consume later.
- Contract fields map from warehouse columns: `invoice` → `invoice_id`, `customer_id` (nullable), `country`, `invoice_date` (ISO 8601), `line_total` → `invoice_total`, `description` optionally in `content`.
- Option A (invoice-level) recommended: one document per unique `Invoice`; content = concatenated line summaries.
- RAG team decides on integration path when ready; warehouse schema remains separate.

**Bottom line:** The warehouse and RAG systems are decoupled. The audit findings feed the pipeline design; no pipeline code is implemented in this document.

---
## 12. Audit Conclusion

This audit has documented the quality profile of the Online Retail II dataset across 1,067,371 rows and 8 columns. All findings are consistent with the initial profiling run and are reproduced verbatim without invention. Statistics reflect the initial profiling run; full-dataset timestamp parsing and validation remain pending pipeline implementation.

**Key decisions confirmed:**
1. Missing `Description` and `Customer ID` values are kept nullable — no artificial substitution.
2. Negative quantities are preserved as-is; no sign-flip or rejection.
3. Zero prices are preserved; not rejected or altered.
4. The 5 negative-price rows are quarantined for investigation; excluded from validated warehouse set.
5. Exact duplicate rows (34,335 excess) are reported and investigated; no automatic deletion.
6. `Invoice` stored as TEXT to preserve alpha prefixes (`5`, `4`, `C`, `A`).
7. Dates: format confirmed; parsing and validation pending full-dataset execution.
8. Original CSV is preserved unchanged; the pipeline must not modify the raw source file.

**No Python code, database migrations, or schema changes are implemented in this document.** The audit serves as a design reference for the pipeline implementation phase. All statistics are sourced from the dataset profiling and are verified against the actual CSV file.

*The original CSV is preserved unchanged. All intermediate artifacts (profiles, cleaned, rejected, quarantined) are written to `pipeline/data/cleaned/`, `pipeline/data/rejected/`, and `pipeline/data/quarantined/` respectively.*

*End of audit report.*