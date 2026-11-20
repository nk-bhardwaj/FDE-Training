-- Day 4: add source_id to documents for idempotent ingestion.
--
-- Adds a source_id column with a unique constraint to the documents table,
-- enabling the RAG ingestion pipeline to identify existing documents and
-- update them instead of creating duplicates when re-ingesting the same
-- source.
--
-- Target: Neon PostgreSQL with the `vector` extension already enabled.
-- If it is not, enable it once as the database owner:
--     CREATE EXTENSION IF NOT EXISTS vector;
--
-- Apply with:
--     psql "$DATABASE_URL" -f migrations/004_add_source_id_to_documents.sql
--
-- Note: This migration adds a UNIQUE constraint on source_id. Existing
-- documents that do not have a source_id will receive a NULL value, which
-- is permitted by the unique constraint (NULLs are considered distinct).

BEGIN;

-- Add source_id column if not already present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'source_id'
    ) THEN
        ALTER TABLE documents ADD COLUMN source_id TEXT UNIQUE;
    END IF;
END$$;

COMMIT;