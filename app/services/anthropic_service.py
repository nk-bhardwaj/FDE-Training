import os
import time

from anthropic import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from dotenv import load_dotenv

from app.core.logging import get_logger
from app.services.llm_errors import (
    LLMProviderError,
    LLMTimeoutError,
    MissingAPIKeyError,
)

logger = get_logger(__name__)


class AnthropicService:
    def __init__(self, timeout: float | None = None) -> None:
        load_dotenv()
        if timeout is None:
            raw_timeout = os.getenv("LLM_REQUEST_TIMEOUT", "30.0")
            try:
                timeout = float(raw_timeout)
            except (TypeError, ValueError) as exc:
                raise ValueError("LLM_REQUEST_TIMEOUT must be a valid number") from exc
            if timeout <= 0:
                raise ValueError("LLM_REQUEST_TIMEOUT must be a positive number")
        self.timeout = timeout
        self._client: AsyncAnthropic | None = None

    def _get_client(self) -> AsyncAnthropic:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("Anthropic API key is not configured")

        if self._client is None:
            self._client = AsyncAnthropic(api_key=api_key, timeout=self.timeout)
        return self._client

    async def generate_response(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-5",
    ) -> tuple[str, str, float, dict[str, int | None]]:
        client = self._get_client()
        start = time.perf_counter()

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = (time.perf_counter() - start) * 1000
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "input_tokens", None) if usage else None
            output_tokens = getattr(usage, "output_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None
            if total_tokens is None and input_tokens is not None and output_tokens is not None:
                total_tokens = input_tokens + output_tokens
            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
                "anthropic",
                model,
                latency_ms,
                input_tokens,
                output_tokens,
                total_tokens,
            )
            if not response.content:
                return (
                    "",
                    model,
                    latency_ms,
                    {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                    },
                )
            first = response.content[0]
            return (
                getattr(first, "text", "") or "",
                model,
                latency_ms,
                {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                },
            )
        except AuthenticationError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=authentication",
                "anthropic",
                latency_ms,
            )
            raise LLMProviderError("Anthropic authentication failed", status_code=502) from exc
        except RateLimitError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=rate_limit",
                "anthropic",
                latency_ms,
            )
            raise LLMProviderError("Anthropic rate limit exceeded", status_code=429) from exc
        except (APITimeoutError, TimeoutError) as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=timeout",
                "anthropic",
                latency_ms,
            )
            raise LLMTimeoutError("Anthropic request timed out") from exc
        except APIConnectionError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=connection",
                "anthropic",
                latency_ms,
            )
            raise LLMProviderError("Anthropic service is unavailable", status_code=502) from exc
        except APIError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=provider_error",
                "anthropic",
                latency_ms,
            )
            raise LLMProviderError("Anthropic request failed", status_code=502) from exc
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "provider=%s status=failure latency_ms=%.2f reason=unexpected",
                "anthropic",
                latency_ms,
            )
            raise LLMProviderError("Anthropic request failed", status_code=502) from exc
