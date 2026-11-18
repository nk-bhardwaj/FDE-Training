# AI Provider Comparison

**Project:** FDE AI Sprint  
**Document status:** Current as of 2026-11-18  
**Scope:** OpenAI, Anthropic, and Groq integrations as implemented in this repository

## 1. Overview

### Why multiple AI providers

A single provider ties the product to one vendor's model lifecycle, pricing, rate limits, and outage domain. We integrated OpenAI, Anthropic, and Groq so the same application can:

- Compare response quality, latency, and token cost on identical prompts.
- Route work to a provider whose model class fits the task.
- Keep serving requests when one provider degrades or rate-limits us.
- Avoid a forced migration when a provider retires a model.
- Evaluate new models without changing client code.

### Benefits of a provider-independent architecture

All traffic enters through one endpoint, `POST /api/chat`, and the caller selects a provider with a single `provider` field. The rest of the system is shared:

- `app/schemas/llm.py` defines one request shape (`LLMRequest`) and one response shape (`LLMResponse`) for every provider.
- `app/services/llm_service.py` dispatches by provider name and hides the SDK services behind one method, `generate_response(provider, prompt)`.
- `app/api/routes/llm.py` maps provider errors to one HTTP error contract, so clients do not need provider-specific error handling.
- `app/core/logging.py` emits the same structured fields for all providers.

Each provider's SDK-specific code stays isolated in its own service module. Adding a provider means adding a service, registering it in the dispatcher, and extending the `ProviderName` literal — the API client is unchanged. Conversely, swapping a model default is a local change to one service module plus its tests.

## 2. SDK and Integration Comparison

| Aspect | OpenAI | Anthropic | Groq |
|---|---|---|---|
| Official Python SDK | `openai` | `anthropic` | `groq` |
| Async client | `AsyncOpenAI` | `AsyncAnthropic` | `AsyncGroq` |
| SDK method used | `client.chat.completions.create(...)` | `client.messages.create(...)` | `client.chat.completions.create(...)` |
| API surface | Chat Completions | Messages | Chat Completions-compatible |
| Service module | `app/services/openai_service.py` | `app/services/anthropic_service.py` | `app/services/groq_service.py` |
| Configured model default | `gpt-4o-mini` | `claude-sonnet-4-5` | `openai/gpt-oss-120b` |
| Credential | `OPENAI_API_KEY` | `ANTHROPIC_API_KEY` | `GROQ_API_KEY` |
| Output limit in our call | Not set | `max_tokens=1024` | Not set |

**Async clients.** Every service instantiates an async SDK client and is awaited from the async FastAPI route. No synchronous SDK method is used in the request path. Clients are created lazily on the first request and cached on the service instance.

**Authentication.** Each service reads its own environment variable at client creation time and passes the key to the SDK constructor. A missing key raises `MissingAPIKeyError` before any network call, which the route maps to HTTP 503. Credentials are never included in logs or responses.

**API integration approach.** We send one user-role message built from the request prompt. Text extraction differs by SDK: OpenAI and Groq read `choices[0].message.content`; Anthropic reads `content[0].text` and returns an empty string when the content list is empty. Anthropic is the only integration that sets an explicit output cap.

**Model selection.** Models are hard-coded defaults in each service's `generate_response` signature. `LLMRequest` has no `model` field, so callers cannot select a model at runtime; changing one requires a code change and a test update.

## 3. Feature Comparison

| Feature | OpenAI | Anthropic | Groq |
|---|---|---|---|
| Token usage tracking | Reads `usage.prompt_tokens`, `completion_tokens`, `total_tokens` | Reads `usage.input_tokens`, `output_tokens`; computes total as their sum when the provider omits it | Reads `usage.prompt_tokens`, `completion_tokens`, `total_tokens` |
| Request latency tracking | `time.perf_counter()` around the awaited SDK call; returned as `latency_ms` | Same | Same |
| Error handling | SDK errors mapped to the shared error types | Same mapping | Same mapping |
| Timeout configuration | `LLM_REQUEST_TIMEOUT`, default `30.0` seconds | Same | Same |
| Logging | Structured success/failure events via `get_logger` | Same | Same |
| API response consistency | `LLMResponse` with `provider`, `response`, `model`, `latency_ms`, `usage` | Same schema | Same schema |

**Error handling.** The route converts shared exceptions into HTTP responses: missing key → 503, timeout → 504, rate limit → 429, authentication or other provider error → 502, validation error → 400. All three services implement the same catch order for `AuthenticationError`, `RateLimitError`, `APITimeoutError`/`TimeoutError`, `APIConnectionError`, `APIError`, and unexpected exceptions. Unexpected exceptions are logged with a stack trace but returned to the client as a generic provider failure.

**Timeout configuration.** Each service validates `LLM_REQUEST_TIMEOUT` at construction: it must parse as a float and be greater than zero, otherwise startup fails with `ValueError`. The parsed value is passed to the SDK client as its request timeout. An explicit `timeout` argument to a service constructor overrides the environment variable.

**Logging.** Logging is centralized in `app/core/logging.py`: console output plus a rotating `logs/app.log` (1 MB per file, 3 backups), controlled by `LOG_LEVEL`. Successful requests log provider, model, latency, and token counts. Failures log a reason code (`authentication`, `rate_limit`, `timeout`, `connection`, `provider_error`, `unexpected`) rather than provider internals.

**API response consistency.** Despite different SDK response shapes, the route always returns the same JSON keys. `usage` always contains `input_tokens`, `output_tokens`, and `total_tokens`; individual values may be `null` when the provider does not report them.

## 4. Model Comparison

### Models configured in this implementation

| Provider | Model ID in code | Lifecycle status (2026-11-18) | Notes |
|---|---|---|---|
| OpenAI | `gpt-4o-mini` | **Deprecated** — alias of `gpt-4o-mini-2024-07-18`; OpenAI shutdown date 2027-01-14 | Still wired as the default, but not supported for new work |
| Anthropic | `claude-sonnet-4-5` | **Deprecated** — alias of `claude-sonnet-4-5-20250929`; deprecation 2026-09-30, retirement 2026-11-30 | Still wired as the default, but not supported for new work |
| Groq | `openai/gpt-oss-120b` | **Active** — listed in Groq's supported models | Current default for this integration |

Only `openai/gpt-oss-120b` in the table above is an active model. The other two are deprecated by their providers and are **not** listed here as currently supported; they remain in the code only as existing defaults and should be treated as migration items. Provider-recommended replacements (`gpt-6-luna` for OpenAI, `claude-sonnet-5-5` for Anthropic) are **not configured in this project** and would require code and test changes before use.

### Differences between the configured models

- **OpenAI `gpt-4o-mini`** — a compact general-purpose chat model from the GPT-4o family, historically chosen for low-cost, low-latency text tasks. Our integration uses it through the Chat Completions endpoint with no explicit output cap. Its deprecated status means it should not be used for new workloads.
- **Anthropic `claude-sonnet-4-5`** — a balanced Sonnet-class model from Anthropic's Claude 4.5 generation, used through the Messages endpoint. Our integration caps its output at 1024 tokens and derives `total_tokens` from input and output counts when the API omits it. It is deprecated and retires 2026-11-30.
- **Groq `openai/gpt-oss-120b`** — OpenAI's open-weight 120B-parameter mixture-of-experts model served on Groq's inference platform. It is designed for reasoning and agentic tasks and is the only configured default that is currently active on its provider. Our integration calls it through Groq's Chat Completions-compatible endpoint.

The three defaults are not equivalent: they come from different model families, use different endpoints, and differ in output limiting and usage reporting. Comparisons drawn from this API therefore compare whole integrations, not just model quality.

## 5. Performance Comparison

### How we measure

- **Latency (`latency_ms`):** wall-clock time around the awaited SDK call, measured with `time.perf_counter()` and converted to milliseconds. It excludes request validation, provider dispatch, logging, and the client-to-API HTTP hop. It is returned in every response and logged on success and failure.
- **Token usage (`usage`):** provider-reported counts mapped to `input_tokens`, `output_tokens`, and `total_tokens`. We do not estimate tokens locally. A value can be `null` when the provider omits it; for Anthropic, `total_tokens` is computed from input plus output when absent.

These metrics are useful for tracking one integration over time. Cross-provider comparisons require the same prompts, similar output lengths, the same environment, and enough samples to smooth out variance. Anthropic's fixed 1024-token cap and the models' different reasoning behavior make single-request latency comparisons misleading.

### Benchmark table

No benchmark run is recorded in this repository. The table is intentionally unpopulated rather than filled with estimated figures.

| Provider | Model | Samples | p50 latency (ms) | p95 latency (ms) | Avg input tokens | Avg output tokens | Source |
|---|---|---|---|---|---|---|---|
| OpenAI | `gpt-4o-mini` | Not measured | Not measured | Not measured | Not measured | Not measured | No benchmark data in repo |
| Anthropic | `claude-sonnet-4-5` | Not measured | Not measured | Not measured | Not measured | Not measured | No benchmark data in repo |
| Groq | `openai/gpt-oss-120b` | Not measured | Not measured | Not measured | Not measured | Not measured | No benchmark data in repo |

To populate it, send an identical prompt set to `POST /api/chat` for each provider, record `latency_ms` and the three `usage` fields from each response, compute p50/p95 latency and mean token counts, and record the run date, model IDs, SDK versions, and environment alongside the results.

## References

- `app/main.py`, `app/api/router.py`, `app/api/routes/llm.py`
- `app/schemas/llm.py`, `app/services/llm_service.py`, `app/services/llm_errors.py`
- `app/services/openai_service.py`, `app/services/anthropic_service.py`, `app/services/groq_service.py`
- `app/core/logging.py`, `README.md`
- [OpenAI model deprecations](https://developers.openai.com/api/docs/deprecations)
- [Anthropic model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations)
- [Groq supported models](https://console.groq.com/docs/models)
