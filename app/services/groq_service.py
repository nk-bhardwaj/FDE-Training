import os
import time

from groq import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncGroq,
    AuthenticationError,
    RateLimitError,
)

from app.core.logging import get_logger
from app.schemas.llm import LLMGeneration
from app.services.llm_errors import (
    LLMProviderError,
    LLMTimeoutError,
    MissingAPIKeyError,
)

logger = get_logger(__name__)


class GroqService:
    def __init__(self, timeout: float | None = None) -> None:
        if timeout is None:
            raw_timeout = os.getenv("LLM_REQUEST_TIMEOUT", "30.0")
            try:
                timeout = float(raw_timeout)
            except (TypeError, ValueError) as exc:
                raise ValueError("LLM_REQUEST_TIMEOUT must be a valid number") from exc
            if timeout <= 0:
                raise ValueError("LLM_REQUEST_TIMEOUT must be a positive number")
        self.timeout = timeout
        self._client: AsyncGroq | None = None

    def _get_client(self) -> AsyncGroq:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("Groq API key is not configured")

        if self._client is None:
            self._client = AsyncGroq(api_key=api_key, timeout=self.timeout)
        return self._client

    async def generate_response(
        self,
        prompt: str,
        model: str = "openai/gpt-oss-120b",
    ) -> LLMGeneration:
        client = self._get_client()
        start = time.perf_counter()

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = (time.perf_counter() - start) * 1000
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            output_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None
            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
                "groq",
                model,
                latency_ms,
                input_tokens,
                output_tokens,
                total_tokens,
            )
            content = response.choices[0].message.content
            return (
                content or "",
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
                "groq",
                latency_ms,
            )
            raise LLMProviderError("Groq authentication failed", status_code=502) from exc
        except RateLimitError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=rate_limit",
                "groq",
                latency_ms,
            )
            raise LLMProviderError("Groq rate limit exceeded", status_code=429) from exc
        except (APITimeoutError, TimeoutError) as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=timeout",
                "groq",
                latency_ms,
            )
            raise LLMTimeoutError("Groq request timed out") from exc
        except APIConnectionError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=connection",
                "groq",
                latency_ms,
            )
            raise LLMProviderError("Groq service is unavailable", status_code=502) from exc
        except APIError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=provider_error",
                "groq",
                latency_ms,
            )
            raise LLMProviderError("Groq request failed", status_code=502) from exc
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "provider=%s status=failure latency_ms=%.2f reason=unexpected",
                "groq",
                latency_ms,
            )
            raise LLMProviderError("Groq request failed", status_code=502) from exc
