-- Day 3: keyword search with PostgreSQL full-text search.
--
-- Adds a generated tsvector column and GIN index for keyword search.
-- The column automatically maintains its value for all existing and future documents.
--
-- Apply with:
--     psql "$DATABASE_URL" -f migrations/002_keyword_search.sql

BEGIN;

-- Add generated stored tsvector column
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS tsvector_content tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english'::regconfig, coalesce(content, ''))
    ) STORED;

-- GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_documents_tsvector_content_gin
    ON documents
    USING gin (tsvector_content);

COMMIT;