-- Warehouse schema for the cleaned Online Retail II dataset.
--
-- Creates a dedicated `warehouse` schema and the
-- `warehouse.cleaned_online_retail_ii` table described in
-- pipeline/docs/schema-design.md (Sections 2-6), plus the documented indexes.
--
-- This migration is additive and isolated from the Week 1 RAG objects:
-- it does not read, alter, or drop `public.documents` or
-- `public.document_chunks`, and it does not create or modify extensions.
--
-- Safe to re-run: every statement uses IF NOT EXISTS. If the table already
-- exists, its existing definition is left untouched (a pre-existing table
-- with a different shape is not automatically altered).
--
-- Apply with:
--     psql "$DATABASE_URL" -f migrations/005_create_warehouse_schema.sql
--
-- Do not commit credentials. DATABASE_URL is read from the environment.

BEGIN;

-- 1. Dedicated schema, separate from the RAG `public` schema.
CREATE SCHEMA IF NOT EXISTS warehouse;

-- 2. Target warehouse table (schema-design.md Section 3).
CREATE TABLE IF NOT EXISTS warehouse.cleaned_online_retail_ii (
    source_row_id       BIGINT PRIMARY KEY,
    invoice             TEXT NOT NULL,
    stock_code          TEXT NOT NULL,
    description         TEXT,
    quantity            BIGINT NOT NULL,
    invoice_timestamp   TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    price               NUMERIC(12, 4) NOT NULL,
    customer_id         TEXT,
    country             TEXT NOT NULL,
    invoice_date        DATE NOT NULL,
    line_total          NUMERIC(14, 4) NOT NULL,
    invoice_month       TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Documented query-support indexes (schema-design.md Section 6).
--    source_row_id needs no extra index: the PRIMARY KEY already creates one.
CREATE INDEX IF NOT EXISTS idx_cleaned_retail_customer_id
    ON warehouse.cleaned_online_retail_ii (customer_id);

CREATE INDEX IF NOT EXISTS idx_cleaned_retail_invoice_ts
    ON warehouse.cleaned_online_retail_ii (invoice_timestamp);

CREATE INDEX IF NOT EXISTS idx_cleaned_retail_country
    ON warehouse.cleaned_online_retail_ii (country);

COMMIT;
