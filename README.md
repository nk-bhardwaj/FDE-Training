# FDE AI Sprint

Multi-provider AI backend built with FastAPI. Exposes a single unified chat endpoint that routes requests to OpenAI, Anthropic, or Groq.

## Tech Stack

- Python 3.13+
- FastAPI
- Uvicorn
- Pydantic
- uv
- OpenAI SDK
- Anthropic SDK
- Groq SDK
- Pytest
- Ruff

## Features

- Multi-provider LLM integration (OpenAI, Anthropic, Groq)
- Unified `POST /api/chat` endpoint
- Asynchronous provider communication
- Configurable request timeout via `LLM_REQUEST_TIMEOUT`
- Centralized logging with rotation
- Input, output, and total token tracking
- Model name and request latency tracking
- Consistent error handling across providers
- Automated tests

## Project Structure

```
app/
  api/
    router.py
    routes/llm.py
  core/
    logging.py
  schemas/
    llm.py
  services/
    anthropic_service.py
    groq_service.py
    llm_errors.py
    llm_service.py
    openai_service.py
  main.py
  cli.py
tests/
  test_llm.py
  test_main.py
  test_logging.py
```

## Prerequisites

- Python 3.13 or newer
- uv

## Installation and Setup

```powershell
git clone <repository-url>
cd fde-ai-sprint
uv sync --dev
Copy-Item .env.example .env
```

Configure `.env` with your API keys. Never commit real keys.

Environment variables:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GROQ_API_KEY`
- `LLM_REQUEST_TIMEOUT` (default `30.0`)
- `LOG_LEVEL` (default `INFO`)

## Running the Application

Development:

```powershell
uv run dev
```

Production:

```powershell
uv run start
```

Server URL: `http://localhost:8000`

Documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Documentation

### `POST /api/chat`

Request body:

```json
{
  "provider": "openai",
  "prompt": "Hello"
}
```

Supported providers: `openai`, `anthropic`, `groq`.

Response:

```json
{
  "provider": "openai",
  "response": "...",
  "model": "gpt-4o-mini",
  "latency_ms": 123.45,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 20,
    "total_tokens": 30
  }
}
```

Examples:

OpenAI:

```json
{"provider": "openai", "prompt": "Hello"}
```

Anthropic:

```json
{"provider": "anthropic", "prompt": "Hello"}
```

Groq:

```json
{"provider": "groq", "prompt": "Hello"}
```

### `GET /health`

Returns server health status.

## Testing and Code Quality

Run tests:

```powershell
uv run pytest
```

Coverage:

```powershell
uv run pytest --cov=app
```

Lint:

```powershell
uv run ruff check .
```

Format check:

```powershell
uv run ruff format --check .
```

## Logging and Error Handling

Centralized logging writes to console and `logs/app.log` with rotation (1MB, 3 backups). Log level via `LOG_LEVEL`.

Error scenarios:

- Missing API key: 503
- Timeout: 504
- Rate limit: 429
- Authentication/provider errors: 502
- Invalid request: 400

## Environment Variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GROQ_API_KEY` | Groq API key |
| `LLM_REQUEST_TIMEOUT` | Provider request timeout (seconds) |
| `LOG_LEVEL` | Logging level |

## Git and Development Workflow

```powershell
uv sync --dev
uv add <package>
uv remove <package>
```
