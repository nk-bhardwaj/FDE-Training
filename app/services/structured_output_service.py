import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.schemas.llm import LLMGeneration
from app.schemas.structured_output import (
    ProviderName,
    StructuredChatResponse,
    SupportAnalysis,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class StructuredOutputError(Exception):
    """Raised when structured output cannot be produced after retries."""


class StructuredOutputService:
    def __init__(self, llm_service: LLMService | None = None, max_retries: int = 1) -> None:
        self.llm_service = llm_service or LLMService()
        self.max_retries = max_retries
        self._prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        self.system_prompt = (self._prompts_dir / "structured_support_v1.txt").read_text(
            encoding="utf-8"
        )

    async def analyze_support(
        self,
        provider: ProviderName,
        message: str,
    ) -> StructuredChatResponse:
        attempts = 0
        total_latency_ms = 0.0
        accumulated_usage: dict[str, int | None] = {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }
        model = ""
        last_error: str | None = None
        previous_output: str | None = None

        while attempts < self.max_retries + 1:
            attempts += 1
            user_message = message
            if last_error is not None and previous_output is not None:
                user_message = (
                    f"{message}\n\n"
                    f"Previous output: {previous_output}\n"
                    f"Validation error: {last_error}\n"
                    "Please fix the output and return only valid JSON matching the schema."
                )

            generation: LLMGeneration = await self.llm_service.generate_response(
                provider=provider,
                prompt=user_message,
                system_prompt=self.system_prompt,
            )
            response_text, model, latency_ms, usage = generation
            total_latency_ms += latency_ms
            if usage:
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    value = usage.get(key)
                    if value is not None:
                        accumulated_usage[key] = (accumulated_usage.get(key) or 0) + value

            try:
                data = json.loads(response_text)
                analysis = SupportAnalysis(**data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = str(exc)
                previous_output = response_text
                logger.warning(
                    "Structured output validation failed provider=%s attempt=%s error=%s",
                    provider,
                    attempts,
                    last_error,
                )
                continue

            return StructuredChatResponse(
                provider=provider,
                analysis=analysis,
                model=model,
                latency_ms=total_latency_ms,
                usage=accumulated_usage,
                attempts=attempts,
            )

        raise StructuredOutputError(
            f"Failed to produce valid structured output for provider {provider} after {attempts} attempts"
        )
