"""RAG answer generation service.

Generates a grounded answer from an :class:`AssembledContext` using the existing
``LLMService`` abstraction, then validates and hydrates the model's citation
labels into authoritative source metadata.

Retrieved context is treated as untrusted data. Citation labels are the only
identifiers the model is allowed to emit; unknown or duplicate labels are
rejected and the model is retried once with the validation error appended,
mirroring ``StructuredOutputService``.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from app.core.logging import get_logger
from app.schemas.llm import ProviderName, TokenUsage
from app.schemas.rag_answer import Citation, RAGAnswerPayload, RAGAnswerResponse
from app.services.context_engineering_service import AssembledContext
from app.services.llm_service import LLMService
from app.services.rag_prompt_builder import BuiltPrompt, RAGPromptBuilder

logger = get_logger(__name__)

ABSTENTION_MESSAGE = "I don't know based on the available information."
DEFAULT_MAX_RETRIES = 1


class RAGAnswerError(Exception):
    """Raised when a valid grounded answer cannot be produced after retries."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class _CitationValidationError(Exception):
    """Raised when returned citation labels are unknown or duplicated."""


class _MissingCitationsError(Exception):
    """Raised when a non-abstained answer cites no context at all."""


class RAGAnswerService:
    """Produces grounded, cited answers from an assembled retrieval context."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        *,
        prompt_path: Path | None = None,
        prompt_builder: RAGPromptBuilder | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be zero or greater")
        self.llm_service = llm_service or LLMService()
        self.prompt_builder = prompt_builder or RAGPromptBuilder()
        self.max_retries = max_retries
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        self.prompt_path = prompt_path or prompts_dir / "rag_answer_v1.txt"
        self.system_prompt = self.prompt_path.read_text(encoding="utf-8")

    async def answer(
        self,
        provider: ProviderName,
        question: str,
        context: AssembledContext,
    ) -> RAGAnswerResponse:
        """Answer ``question`` using only ``context``.

        Args:
            provider: The LLM provider to use.
            question: The user's question. Must not be blank.
            context: Retrieved, attributed context prepared by
                ``ContextEngineeringService``.

        Returns:
            A grounded answer with hydrated citations, or a canonical
            abstention when the context is empty or insufficient.

        Raises:
            ValueError: If ``question`` is empty or whitespace only.
            RAGAnswerError: If the model cannot produce a valid, cited answer
                after the configured retries.
            MissingAPIKeyError: Propagated unchanged from the provider layer.
            LLMTimeoutError: Propagated unchanged from the provider layer.
            LLMProviderError: Propagated unchanged from the provider layer.
        """
        if not question or not question.strip():
            raise ValueError("question must not be empty")

        if not context.chunks:
            logger.info(
                "service=rag_answer operation=answer status=abstained "
                "reason=empty_context provider=%s context_chunks=0 context_tokens=%d",
                provider,
                context.total_tokens,
            )
            return self._abstention_response(
                provider=provider,
                question=question,
                context=context,
                attempts=0,
            )

        built = self.prompt_builder.build(question, context)
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
        last_failure_was_missing_citations = False

        while attempts < self.max_retries + 1:
            attempts += 1
            user_prompt = self._render_attempt_prompt(built, last_error, previous_output)

            response_text, model, latency_ms, usage = await self.llm_service.generate_response(
                provider=provider,
                prompt=user_prompt,
                system_prompt=self.system_prompt,
            )
            total_latency_ms += latency_ms
            self._accumulate_usage(accumulated_usage, usage)

            try:
                payload = self._parse_payload(response_text)
                if payload.abstained:
                    logger.info(
                        "service=rag_answer operation=answer status=abstained "
                        "reason=model_abstained provider=%s model=%s attempts=%d "
                        "context_chunks=%d context_tokens=%d latency_ms=%.2f",
                        provider,
                        model,
                        attempts,
                        len(context.chunks),
                        context.total_tokens,
                        total_latency_ms,
                    )
                    return self._abstention_response(
                        provider=provider,
                        question=question,
                        context=context,
                        model=model,
                        latency_ms=total_latency_ms,
                        usage=self._to_token_usage(accumulated_usage),
                        attempts=attempts,
                    )

                citations = self._resolve_citations(payload.citations, built)
                if not citations:
                    raise _MissingCitationsError(
                        "answer must cite at least one context label; "
                        "otherwise set abstained to true"
                    )
            except _MissingCitationsError as exc:
                last_error = str(exc)
                previous_output = response_text
                last_failure_was_missing_citations = True
                self._log_retry(provider, attempts, exc)
                continue
            except (_CitationValidationError, ValidationError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                previous_output = response_text
                last_failure_was_missing_citations = False
                self._log_retry(provider, attempts, exc)
                continue

            logger.info(
                "service=rag_answer operation=answer status=success provider=%s model=%s "
                "attempts=%d citations=%d context_chunks=%d context_tokens=%d latency_ms=%.2f",
                provider,
                model,
                attempts,
                len(citations),
                len(context.chunks),
                context.total_tokens,
                total_latency_ms,
            )
            return RAGAnswerResponse(
                question=question,
                answer=payload.answer.strip(),
                citations=citations,
                abstained=False,
                provider=provider,
                model=model,
                latency_ms=total_latency_ms,
                usage=self._to_token_usage(accumulated_usage),
                attempts=attempts,
                context_chunks=len(context.chunks),
                context_tokens=context.total_tokens,
            )

        if last_failure_was_missing_citations:
            logger.warning(
                "service=rag_answer operation=answer status=abstained "
                "reason=missing_citations provider=%s model=%s attempts=%d "
                "context_chunks=%d context_tokens=%d latency_ms=%.2f",
                provider,
                model,
                attempts,
                len(context.chunks),
                context.total_tokens,
                total_latency_ms,
            )
            return self._abstention_response(
                provider=provider,
                question=question,
                context=context,
                model=model,
                latency_ms=total_latency_ms,
                usage=self._to_token_usage(accumulated_usage),
                attempts=attempts,
            )

        logger.warning(
            "service=rag_answer operation=answer status=failure provider=%s model=%s "
            "attempts=%d reason=invalid_output error=%s latency_ms=%.2f",
            provider,
            model,
            attempts,
            last_error,
            total_latency_ms,
        )
        raise RAGAnswerError(
            f"Failed to produce a valid cited answer for provider {provider} "
            f"after {attempts} attempts"
        )

    @staticmethod
    def _render_attempt_prompt(
        built: BuiltPrompt,
        last_error: str | None,
        previous_output: str | None,
    ) -> str:
        """Return the original prompt, or the retry prompt with the last error."""
        if last_error is None or previous_output is None:
            return built.user_prompt
        return (
            f"{built.user_prompt}\n\n"
            f"Previous output: {previous_output}\n"
            f"Validation error: {last_error}\n"
            "Please fix the output and return only valid JSON matching the schema."
        )

    @staticmethod
    def _parse_payload(response_text: str) -> RAGAnswerPayload:
        """Parse the model output, tolerating a surrounding markdown code fence."""
        return RAGAnswerPayload.model_validate_json(_strip_code_fence(response_text))

    @staticmethod
    def _resolve_citations(
        labels: list[str],
        built: BuiltPrompt,
    ) -> list[Citation]:
        """Map citation labels to authoritative citations.

        Unknown and duplicate labels are rejected. Valid citations keep their
        first-occurrence order.
        """
        seen: set[str] = set()
        citations: list[Citation] = []
        for raw_label in labels:
            label = raw_label.strip()
            if label not in built.labels:
                raise _CitationValidationError(f"Unknown citation label: {raw_label!r}")
            if label in seen:
                raise _CitationValidationError(f"Duplicate citation label: {raw_label!r}")
            seen.add(label)
            chunk = built.labels[label]
            citations.append(
                Citation(
                    source_id=chunk.source_id,
                    document_title=chunk.document_title,
                    chunk_index=chunk.chunk_index,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                )
            )
        return citations

    @staticmethod
    def _accumulate_usage(
        accumulated: dict[str, int | None],
        usage: dict[str, int | None] | None,
    ) -> None:
        """Sum token usage across attempts, preserving ``None`` for missing keys."""
        if not usage:
            return
        for key in accumulated:
            value = usage.get(key)
            if value is not None:
                accumulated[key] = (accumulated[key] or 0) + value

    @staticmethod
    def _to_token_usage(accumulated: dict[str, int | None]) -> TokenUsage | None:
        """Convert accumulated usage to a schema model, or ``None`` if unknown."""
        if all(value is None for value in accumulated.values()):
            return None
        return TokenUsage(**accumulated)

    def _abstention_response(
        self,
        *,
        provider: ProviderName,
        question: str,
        context: AssembledContext,
        model: str = "",
        latency_ms: float = 0.0,
        usage: TokenUsage | None = None,
        attempts: int = 0,
    ) -> RAGAnswerResponse:
        """Build the canonical abstention response."""
        return RAGAnswerResponse(
            question=question,
            answer=ABSTENTION_MESSAGE,
            citations=[],
            abstained=True,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            usage=usage,
            attempts=attempts,
            context_chunks=len(context.chunks),
            context_tokens=context.total_tokens,
        )

    @staticmethod
    def _log_retry(provider: ProviderName, attempts: int, exc: Exception) -> None:
        logger.warning(
            "service=rag_answer operation=answer status=retry provider=%s attempt=%d error=%s",
            provider,
            attempts,
            exc,
        )


def _strip_code_fence(text: str) -> str:
    """Strip a surrounding markdown code fence from model output, if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
