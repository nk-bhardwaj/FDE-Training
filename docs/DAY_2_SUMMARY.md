# Day 2 Summary

**Date:** 18 November 2026  
**Final verification:** 19 November 2026

## 1. Day 2 Objectives

The following objectives have been implemented:

- **Prompt engineering and versioned prompt management:** Created `app/prompts/customer_support_v1.txt`, `v2.txt`, `v3.txt`, and `structured_support_v1.txt`. `PromptService.load_prompt(version)` validates supported versions and raises `PromptNotFoundError` for missing prompts. The `/api/chat` endpoint accepts an optional `prompt_version` and passes the selected prompt as the system prompt.
- **Structured outputs with Pydantic validation and retry:** Implemented `SupportAnalysis`, `StructuredChatRequest`, and `StructuredChatResponse`. `StructuredOutputService` parses and validates LLM JSON responses, retries invalid outputs, and tracks latency and token usage.
- **Server-Sent Events (SSE) streaming:** Implemented `POST /api/chat/stream` using FastAPI `StreamingResponse`. Supports `chunk`, `done`, and `error` events, client-disconnect detection, upstream stream cleanup, prompt versions, and token usage reporting.
- **Multi-provider tool calling:** Implemented `POST /api/chat/tools` with provider-specific adapters for OpenAI, Anthropic, and Groq, using a shared tool-calling orchestrator. The orchestrator enforces a maximum of five iterations and raises `ToolCallLimitError` when the limit is exceeded.

## 2. Architecture

### LLM provider abstraction

`app/services/llm_service.py` (`LLMService`) handles provider dispatch for OpenAI, Anthropic, and Groq.

It supports:
- `generate_response()` for standard LLM requests.
- `generate_stream()` for streaming responses.
- `generate_with_tools()` for function/tool calling.

Provider-specific implementations remain in their respective service modules. The shared `LLMGeneration` type alias standardizes generation results.

### Tool registry and mock order lookup

- `app/tools/order_tools.py`: Defines `TOOL_DEFINITIONS`, `TOOL_REGISTRY`, and `get_tool()`.
- `app/data/mock_orders.py`: Contains mock order records for ORD1001, ORD1002, and ORD1003.
- `lookup_order_status(order_id)` validates input and returns order information or `None` for an unknown order.
- Only registered tools can execute. Arbitrary model-generated code is never executed.

### Shared tool-calling orchestrator

`app/tools/orchestrator.py` contains:
- `ToolCallingAdapter` protocol for provider-specific integration.
- `ToolCall` and `ToolTurn` data structures.
- Shared tool execution and result handling.
- `MAX_TOOL_ITERATIONS = 5`.
- `ToolCallLimitError` for exceeding the iteration limit.

Provider adapters handle SDK-specific message formatting, tool calls, result reconstruction, and usage extraction.

## 3. API Endpoints

All endpoints are mounted under the `/api` prefix.

### `POST /api/chat`

Accepts a provider, prompt, and optional prompt version. Loads the selected system prompt, invokes the provider, and returns the generated response with model, latency, and token usage.

### `POST /api/chat/structured`

Accepts a provider and customer message. Returns validated support analysis containing:
- Category
- Sentiment
- Summary
- Suggested resolution
- Human-review recommendation
- Model, latency, token usage, and attempt count

### `POST /api/chat/stream`

Streams generated text through Server-Sent Events.

Supported events:
- `chunk`: Generated text.
- `done`: Model, latency, and token usage.
- `error`: Safe error message.

The endpoint checks client disconnections and closes upstream streams in a `finally` block.

### `POST /api/chat/tools`

Accepts a provider, prompt, and optional model/system prompt. Supplies registered tool definitions to the provider and executes requested tools through the shared orchestrator.

Returns the final response with provider, model, latency, and token usage.

## 4. Testing and Verification

**Final test results:**
- Pytest: **110 passed in 8.82 seconds**.
- Ruff lint: **All checks passed**.
- Ruff formatting: **43 files already formatted**.

**Live Groq tool-calling verification:**

Tested `POST /api/chat/tools` with the prompt:

`What is the current status of order ORD1001?`

Verified response:
- Provider: `groq`
- Model: `openai/gpt-oss-120b`
- Order: `ORD1001`
- Status: `Shipped`
- Estimated delivery: `2026-11-20`
- Tracking number: `TRK12345`
- Input tokens: 222
- Output tokens: 101
- Total tokens: 323

OpenAI and Anthropic implementations are covered by automated tests. Live API verification was performed with Groq; OpenAI and Anthropic live credentials were unavailable.

## 5. Important Engineering Decisions

### Why SSE was chosen

SSE provides incremental token delivery without waiting for the complete response. Client-disconnect detection and upstream stream cleanup help avoid unnecessary provider work.

### Why a shared tool orchestrator was implemented

The iteration limit, tool execution, result handling, and usage normalization are shared across providers. Provider-specific adapters handle differences between SDKs, reducing duplicated orchestration logic.

### Why tool execution uses a registry

Only functions registered in `TOOL_REGISTRY` can execute. Unknown tool names are rejected, preventing arbitrary model-generated code execution.

### Why provider-specific adapters are necessary

OpenAI, Anthropic, and Groq use different tool-call formats, message structures, and usage metadata. The adapter pattern isolates those differences while keeping the orchestration logic provider-independent.

## 6. Final Verification Status

| Area | Status |
|---|---|
| Prompt management | Implemented |
| Structured output and validation | Implemented |
| SSE streaming | Implemented |
| Groq tool calling | Implemented and live-tested |
| OpenAI tool calling | Implemented and automated-tested |
| Anthropic tool calling | Implemented and automated-tested |
| Automated test suite | 110 passed |
| Ruff lint | Passed |
| Ruff formatting | Passed |

**Day 2 core implementation and verification are complete.**