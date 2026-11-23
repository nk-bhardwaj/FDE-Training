-- Day 4: document chunks store for embeddings + hybrid search.
--
-- Stores token-based chunks of source documents alongside their
-- embeddings and full-text search vectors. Each chunk references
-- its parent document via a foreign key with ON DELETE CASCADE so
-- that deleting a document removes all of its chunks.
--
-- Target: Neon PostgreSQL with the `vector` extension already enabled.
-- If it is not, enable it once as the database owner:
--     CREATE EXTENSION IF NOT EXISTS vector;
--
-- Apply with:
--     psql "$DATABASE_URL" -f migrations/003_create_document_chunks.sql
--
-- Note: HNSW + vector_cosine_ops requires pgvector >= 0.5.0.
-- Queries must use the cosine distance operator `<=>` to use this index.

BEGIN;

CREATE TABLE IF NOT EXISTS document_chunks (
    id               BIGSERIAL PRIMARY KEY,
    document_id      BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index      INTEGER NOT NULL,
    content          TEXT NOT NULL,
    embedding        VECTOR(768) NOT NULL,
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure each chunk position within a document is unique.
    CONSTRAINT document_chunks_document_id_chunk_index_key UNIQUE (document_id, chunk_index)
);

-- Approximate nearest-neighbour index for cosine similarity search over chunks.
-- Queries must use the cosine distance operator `<=>` to leverage this index.
CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- GIN index for fast metadata filtering (e.g. metadata->>'section' = 'returns').
CREATE INDEX IF NOT EXISTS document_chunks_metadata_gin_idx
    ON document_chunks
    USING gin (metadata);

-- Generated stored tsvector column for full-text keyword search.
-- Automatically maintained for all existing and future chunks.
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS tsvector_content tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english'::regconfig, coalesce(content, ''))
    ) STORED;

-- GIN index for fast full-text search on chunk content.
CREATE INDEX IF NOT EXISTS document_chunks_tsvector_content_gin_idx
    ON document_chunks
    USING gin (tsvector_content);

COMMIT;