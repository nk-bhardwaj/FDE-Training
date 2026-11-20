# FDE AI Sprint

A multi-provider AI backend built with FastAPI that exposes unified chat and document search endpoints. The application routes LLM requests across OpenAI, Anthropic, and Groq providers, and provides both semantic (pgvector cosine similarity) and keyword (PostgreSQL full-text search) search over documents stored in Neon PostgreSQL with pgvector.

---

## Project Overview

The application serves as a complete AI support assistant backend with:

- **Unified chat API** — single `POST /api/chat` endpoint that routes requests to OpenAI, Anthropic, or Groq, with streaming, tool calling, and structured output support.
- **Semantic search** — cosine-similarity search over 768-dimensional Gemini embeddings stored in pgvector with HNSW approximate nearest-neighbor indexing.
- **Keyword search** — PostgreSQL full-text search using `tsvector`/`ts_rank`/`websearch_to_tsquery`, with OR-based token matching for improved recall.
- **Document store** — 30 sample documents across 10 e-commerce support categories (order tracking, delivery delays, returns/refunds, cancellations, payment failures, damaged products, account login issues, shipping charges, exchanges, customer support).
- **Metadata filtering** — JSONB `@>` containment operator for filtering by source, category, and other document attributes.
- **Error handling and logging** — centralized provider error mapping (502/503/504/429), missing API key detection, timeout handling, and structured console+file logging.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.13 |
| **Web Framework** | FastAPI, Starlette |
| **Dependency Manager** | `uv` |
| **Pydantic** | v2 data validation & serialization |
| **LLM Providers** | OpenAI SDK, Anthropic SDK, Groq SDK, Google GenAI (`gemini-embedding-001`) |
| **Database** | Neon PostgreSQL with `pgvector` extension |
| **Full-Text Search** | PostgreSQL `tsvector`/`ts_rank`/`to_tsquery` |
| **Testing** | `pytest`, `pytest-asyncio` |
| **Linting/Formatting** | `ruff` |
| **Async IO** | `anyio` |

---

## Architecture

### High-Level Layout

```
app/
  api/              # FastAPI routers and route handlers
    router.py       # top-level API router (prefix="/api")
    routes/llm.py   # LLM chat endpoints (/chat, /chat/structured, /chat/stream, /chat/tools)
    routes/documents.py  # search endpoints (/search, /keyword-search)
  core/             # core infrastructure
    logging.py      # rotating console + file handler
  data/             # mock data and sample documents
    mock_orders.py  # order lookup data for tool-calling
    sample_documents.py  # 30 documents across 10 categories
  prompts/          # prompt templates for structured output
  schemas/          # Pydantic request/response models
    llm.py          # LLM request/response schemas
    documents.py    # semantic & keyword search schemas
    structured_output.py  # structured chat analysis schemas
  services/         # business logic
    llm_service.py  # multi-provider LLM routing + error handling
    openai_service.py     # OpenAI provider implementation
    anthropic_service.py  # Anthropic provider implementation
    groq_service.py       # Groq provider implementation
    embedding_service.py  # Gemini embedding generation (768 dim)
    document_service.py   # semantic + keyword search + document store
    llm_errors.py       # MissingAPIKeyError, LLMTimeoutError, LLMProviderError
    prompt_service.py   # prompt file loading
    structured_output_service.py  # JSON schema validation + retry
  tools/            # tool definitions and registry
    orchestrator.py   # shared tool-calling loop (MAX_TOOL_ITERATIONS=5)
    order_tools.py    # lookup_order_status mock tool
tests/              # 179 unit tests (fully mocked, no live API/DB calls)
scripts/            # seed script, evaluation scripts, comparison report
pyproject.toml      # project config, dependencies, scripts
```

### Key Modules

- **`DocumentService`** (`app/services/document_service.py`) — handles document insertion (`INSERT ... content, embedding, metadata`), semantic search (`embedding <=> query_embedding`), and keyword search (`ts_rank(tsvector_content, to_tsquery(...))` with OR token matching).
- **`EmbeddingService`** (`app/services/embedding_service.py`) — wraps Google GenAI `gemini-embedding-001`; 768-dimensional vectors with `RETRIEVAL_DOCUMENT`/`RETRIEVAL_QUERY` task typing; rate-limit and timeout-aware client.
- **`LLMService`** (`app/services/llm_service.py`) — dispatches to OpenAI/Anthropic/Groq providers; maps provider errors to HTTP status codes (502/503/504/429); supports streaming and tool calling.
- **`LLM orchestrator`** (`app/tools/orchestrator.py`) — shared loop limiting tool calls to 5 iterations; executes registered tools (`lookup_order_status`) and returns JSON results.
- **`PromptService`** (`app/services/prompt_service.py`) — loads versioned prompt files (`customer_support_v1.txt`, etc.) from the `app/prompts/` directory.

---

## Core Features

### Multi-Provider LLM Integration

- Three providers configured via environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`).
- `POST /api/chat` routes to the selected provider; unsupported providers return 400.
- Each provider implements `generate_response`, `generate_stream`, and `generate_with_tools`.
- Centralized error handling maps authentication errors to 502, timeouts to 504, rate limits to 429, and other provider errors to 502.

### Unified Chat API

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/chat` | `LLMRequest` | Synchronous chat response with token usage and latency. |
| `POST /api/chat/structured` | `StructuredChatRequest` | Returns `SupportAnalysis` (category, sentiment, summary, suggested_resolution, requires_human). |
| `POST /api/chat/stream` | `LLMRequest` | Server-sent events stream with incremental chunks. |
| `POST /api/chat/tools` | `LLMToolRequest` | LLM response with tool calls; orchestrator executes mock tools (order lookup). |

### Provider Error Handling

- `MissingAPIKeyError` → 503
- `LLMTimeoutError` → 504
- `LLMProviderError` → mapped `status_code` (default 502, e.g. 429 for rate limit)
- `ValueError` → 400 (invalid request, unsupported provider)
- All errors logged with provider, latency, and reason.

### Token Usage and Latency Tracking

- Every response includes `latency_ms` and a `TokenUsage` object (`input_tokens`, `output_tokens`, `total_tokens`).
- Latency measured via `time.perf_counter()` from request receipt to response completion.
- Logged per-request with provider, model, latency, and token counts.

### Text Embeddings and Vector Storage

- Gemini `gemini-embedding-001` model produces 768-dimensional vectors.
- `embed_document(content, task_type=RETRIEVAL_DOCUMENT)` — stores embeddings in the `embedding` column (`VECTOR(768)`).
- `embed_query(query, task_type=RETRIEVAL_QUERY)` — embeds search queries with the same model/dimensions.
- Vectors stored in Neon PostgreSQL; HNSW index (`documents_embedding_hnsw_idx`) on `embedding vector_cosine_ops` enables approximate cosine similarity search via the `<=>` distance operator.

### Semantic Search

- `POST /api/documents/search` — takes `query`, optional `limit` (default 5), optional `metadata_filters`.
- Embeds the query via `EmbeddingService.embed_query()`, then runs:
  ```sql
  SELECT id, content, metadata, created_at,
         embedding <=> %(query_embedding)s AS distance,
         1 - (embedding <=> %(query_embedding)s) AS similarity
  FROM documents
  ORDER BY embedding <=> %(query_embedding)s
  LIMIT %(limit)s
  ```
- Metadata filters applied via `metadata @> %(filters)s` (JSONB containment), fully parameterized.

### Keyword Search

- `POST /api/documents/keyword-search` — takes `query`, optional `limit` (default 5), optional `metadata_filters`.
- After migration `002_keyword_search.sql`, every document gets a generated `tsvector_content` column:
  ```sql
  to_tsvector('english', coalesce(content, '')) STORED
  ```
  with a GIN index `idx_documents_tsvector_content_gin`.
- Query tokens are extracted (alphanumeric sequences) and joined with ` | ` (OR) to build a `to_tsquery('english', %(tsquery)s)` expression, dramatically improving recall over pure AND semantics.
- Ranking via `ts_rank(tsvector_content, to_tsquery('english', %(tsquery)s)) AS rank`, ordered DESC.
- Metadata filtering supported through `metadata @> %(filters)s`.

### Metadata Filtering

- Both semantic and keyword search support `metadata_filters: dict[str, str \| int \| bool] | None`.
- Applied as `WHERE metadata @> %(filters)s` with `Jsonb(dict(metadata_filters))` — fully parameterized, no SQL interpolation.
- Example: `{"source": "faq", "lang": "en"}` matches documents whose JSONB metadata contains both keys/values.

### Search Result Ranking

- **Semantic**: cosine distance `<=>`; lower = closer. Derived similarity `1 - distance` in `[0,1]`.
- **Keyword**: `ts_rank` value in `[0,1]`; higher = more relevant.
- Both ranked within their respective scoring systems; values are NOT compared numerically across methods.

---

## API Documentation

### Base URL

```
http://localhost:8000
```

### Swagger UI

```
http://localhost:8000/docs
```

### Health Check

```
GET /health  →  {"status": "Server is Healthy"}
```

### `POST /api/chat`

Request:

```json
{
  "provider": "openai",    // "anthropic" | "groq" also supported
  "prompt": "Hello, how are you?",
  "prompt_version": "v1"   // optional
}
```

Response:

```json
{
  "provider": "openai",
  "response": "I'm doing well, thank you!",
  "model": "gpt-4o-mini",
  "latency_ms": 123.45,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 20,
    "total_tokens": 30
  }
}
```

Supported providers: `openai`, `anthropic`, `groq`.

---

### `POST /api/documents/search`

Semantic search request:

```json
{
  "query": "Where is my order ORD1001?",
  "limit": 3,
  "metadata_filters": {"source": "web"}   // optional
}
```

Response:

```json
{
  "query": "Where is my order ORD1001?",
  "results": [
    {
      "id": 1,
      "content": "Where is my order ORD1001? I need the tracking information and current status.",
      "metadata": {"category": "order_tracking", "source": "web"},
      "created_at": "2026-01-15T10:30:00Z",
      "similarity": 0.9231
    }
  ],
  "total_results": 1
}
```

Query parameters:
- `query` (required, min_length=1, max_length=1000) — search text.
- `limit` (optional, default=5, ge=1, le=100) — max results to return.
- `metadata_filters` (optional) — JSONB containment filter.

Error handling:
- 400 — invalid query or limit.
- 503 — missing API key or database not configured.
- 504 — timeout.
- 502 — provider or database error.

---

### `POST /api/documents/keyword-search`

Keyword search request (same shape as semantic search):

```json
{
  "query": "My package was supposed to arrive on Friday but it's now Monday and still not here.",
  "limit": 3,
  "metadata_filters": {"category": "delivery_delays"}   // optional
}
```

Response:

```json
{
  "query": "My package was supposed to arrive on Friday but it's now Monday and still not here.",
  "results": [
    {
      "id": 2,
      "content": "My package was supposed to arrive yesterday but the status still shows transit. Can you check the delivery timeline?",
      "metadata": {"category": "delivery_delays", "source": "email"},
      "created_at": "2026-01-14T08:15:00Z",
      "rank": 0.8421
    }
  ],
  "total_results": 1
}
```

The `rank` field is `ts_rank`-derived relevance; not comparable to semantic `similarity`.

Error handling: same status codes as semantic search (`400`, `503`, `504`, `502`).

---

## Embedding and Search Architecture

### Gemini Embedding Model

- **Model**: `gemini-embedding-001`
- **Dimensions**: 768
- **Task types**: `RETRIEVAL_DOCUMENT` (for content), `RETRIEVAL_QUERY` (for search queries).
- Client created once (cached) with timeout from `LLM_REQUEST_TIMEOUT` env var (default 30s).
- Rate-limit (429) and server error (502) handling with appropriate `LLMProviderError` translation.

### Neon PostgreSQL + pgvector

- Table `documents` with columns:
  - `id BIGSERIAL PRIMARY KEY`
  - `content TEXT NOT NULL`
  - `embedding VECTOR(768) NOT NULL`
  - `metadata JSONB NOT NULL DEFAULT '{}'::jsonb`
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- **HNSW index**: `documents_embedding_hnsw_idx` on `embedding vector_cosine_ops` — enables `ORDER BY embedding <=> %(query_embedding)s` to use the approximate nearest-neighbour index.
- **GIN index**: `documents_metadata_gin_idx` on `metadata` — supports `metadata @> %(filters)s` containment queries.
- Migration `001_create_documents.sql` creates the table and both indexes (run once).
- Migration `002_keyword_search.sql` adds `tsvector_content` (generated `to_tsvector('english', coalesce(content, '')) STORED`) and GIN index `idx_documents_tsvector_content_gin` — run after `001`.

### Cosine Distance and Vector Indexing

- Similarity measured by cosine distance: `1 - (a . b) / (||a|| ||b||)`.
- pgvector operator: `<=>` (distance). Query must use this operator for the HNSW index to be effective.
- The comparison script verifies that queries use `<=>`; the HNSW index is built with `vector_cosine_ops`.

### PostgreSQL Full-Text Search

- Generated column: `tsvector_content` = `to_tsvector('english', coalesce(content, '')) STORED`.
- GIN index: `idx_documents_tsvector_content_gin` on `tsvector_content`.
- Keyword search uses OR-based `to_tsquery` built from alphanumeric tokens:
  ```sql
  WHERE tsvector_content @@ to_tsquery('english', 'term1 | term2 | term3')
  ```
- Ranking: `ts_rank(tsvector_content, to_tsquery('english', %(tsquery)s)) AS rank`.
- Metadata filtering via `metadata @> %(filters)s` (JSONB).

### JSONB Metadata Filtering

- Metadata stored as JSONB; filters applied with containment operator: `metadata @> %(filters)s`.
- `Jsonb(dict(metadata_filters))` binds the dict as a parameter — no string interpolation.
- Example filter: `{"category": "order_tracking", "source": "web"}` matches documents whose metadata JSONB contains both keys with matching values.

---

## Search Evaluation

Evaluation performed on 30 sample documents across 10 categories using 10 representative e-commerce support queries. Results from the latest run:

| Metric | Semantic Search | Keyword Search |
|---|---|---|
| **Top-1 Accuracy** | 100% (10/10) | 80% (8/10) |
| **Top-3 Accuracy** | 100% (10/10) | 90% (9/10) |
| **Average Latency** | 6640.52 ms | 5745.22 ms |

- Evaluation uses the 10 queries from `scripts/evaluate_semantic_search.py` (order_tracking, delivery_delays, returns_refunds, cancellations, payment_failures, damaged_products, account_login_issues, shipping_charges, exchanges, customer_support).
- Keyword search recall improved from 0% to 80%/90% after switching from AND-based `websearch_to_tsquery` to OR-based token matching in `DocumentService.keyword_search()`.
- These results are **small-dataset evaluation results**, not production benchmarks. They demonstrate that the OR-based token matching fix materially improves keyword search recall.

For the full evaluation report, see `docs/day-3-search-evaluation.md`.

---

## Project Setup

### Prerequisites

- **Python 3.13** or newer.
- **`uv`** — the Python package installer (faster than `pip`).

### Installation

```powershell
git clone <repository-url>
cd fde-ai-sprint
uv sync --dev
```

### Environment Variable Configuration

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your credentials. Never commit real keys.

Required variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string (e.g. `postgresql://neondb_owner:npg_...@ep-*.neon.tech/neondb?sslmode=require`) |
| `GEMINI_API_KEY` | Google GenAI API key for `gemini-embedding-001` |
| `OPENAI_API_KEY` | OpenAI API key (for `POST /api/chat` with provider `openai`) |
| `ANTHROPIC_API_KEY` | Anthropic API key (for `POST /api/chat` with provider `anthropic`) |
| `GROQ_API_KEY` | Groq API key (for `POST /api/chat` with provider `groq`) |
| `LLM_REQUEST_TIMEOUT` | Provider request timeout in seconds (default `30.0`) |
| `LOG_LEVEL` | Logging level (default `INFO`) |
| `GEMINI_EMBEDDING_MODEL` | Embedding model name (default `gemini-embedding-001`) |

### Application Startup

**Development (with hot-reload):**

```powershell
uv run dev
```

**Production:**

```powershell
uv run start
```

Server URL: `http://localhost:8000`

### Swagger UI

```
http://localhost:8000/docs
```

Redoc: `http://localhost:8000/redoc`

---

## Database Setup

### Required Extensions

Neon PostgreSQL must have the `vector` extension enabled. If not enabled as the database owner:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Migration Execution

1. **Initial schema** (documents table + HNSW + metadata GIN indexes):

   ```powershell
   psql "$DATABASE_URL" -f migrations/001_create_documents.sql
   ```

2. **Keyword search support** (generated tsvector + GIN index):

   ```powershell
   psql "$DATABASE_URL" -f migrations/002_keyword_search.sql
   ```

### Document Seeding

Insert the 30 sample documents:

```powershell
uv run seed-documents
```

Or directly:

```powershell
python scripts/seed_documents.py
```

This calls `DocumentService.insert_document()` for each entry in `app/data/sample_documents.py`, persisting content, embeddings (Gemini), and metadata.

---

## Testing and Code Quality

### Run All Tests

```powershell
uv run pytest
```

### With Coverage

```powershell
uv run pytest --cov=app
```

### Verified Test Results

- **179 tests passed** across `app/` and `tests/`.
- All tests are fully mocked — no Neon or Gemini API calls during test execution.
- Keyword search tests (`tests/test_keyword_search.py`: 13 passed) verify service-level and API-level scenarios (success, empty query, invalid limits, metadata filters, DB errors, response structure, no results).
- Document service tests (`tests/test_document_service.py`: 27 passed) verify insert, semantic search with/without filters, invalid limits, empty queries, error wrapping, and credential privacy (never logged).
- Report generation tests (`tests/test_search_evaluation_report.py`: 10 passed) verify the Markdown report structure, technology stack mentions, dataset details, results table headers, single query results, failure representation, empty results, summary metrics, latency rounding, and observations section.

### Lint and Formatting

```powershell
# Check for linting issues
uv run ruff check .

# Check formatting
uv run ruff format --check .

# Auto-format
uv run ruff format .
```

All 179 tests pass, and Ruff reports **all checks passed** with **57 files already formatted**.

---

## Environment Variables

| Variable | Required? | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | **yes** | — | Neon PostgreSQL connection string |
| `GEMINI_API_KEY` | **yes** | — | Google GenAI API key for embeddings |
| `OPENAI_API_KEY` | optional | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | optional | — | Anthropic API key |
| `GROQ_API_KEY` | optional | — | Groq API key |
| `LLM_REQUEST_TIMEOUT` | no | `30.0` | Seconds before a provider request times out |
| `LOG_LEVEL` | no | `INFO` | Root and per-logger level |
| `GEMINI_EMBEDDING_MODEL` | no | `gemini-embedding-001` | Embedding model name |

The `.env.example` file (in the project root) lists all variable names and purposes. Real credentials must never be committed.

---