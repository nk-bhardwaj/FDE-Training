-- Day 3: document store for embeddings + semantic search.
--
-- Target: Neon PostgreSQL with the `vector` extension already enabled.
-- If it is not, enable it once as the database owner:
--     CREATE EXTENSION IF NOT EXISTS vector;
--
-- Apply with:
--     psql "$DATABASE_URL" -f migrations/001_create_documents.sql
--
-- Note: HNSW + vector_cosine_ops requires pgvector >= 0.5.0.
-- Queries must use the cosine distance operator `<=>` to use this index.

BEGIN;

CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    embedding   VECTOR(768) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Approximate nearest-neighbour index for cosine similarity search.
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
    ON documents
    USING hnsw (embedding vector_cosine_ops);

-- Supports metadata filters (e.g. metadata->>'source' = 'faq').
CREATE INDEX IF NOT EXISTS documents_metadata_gin_idx
    ON documents
    USING gin (metadata);

COMMIT;
