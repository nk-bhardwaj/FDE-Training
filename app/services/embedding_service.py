import os
import time
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from app.core.logging import get_logger
from app.services.llm_errors import (
    LLMProviderError,
    LLMTimeoutError,
    MissingAPIKeyError,
)

logger = get_logger(__name__)

load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

TaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]


class EmbeddingService:
    """Generates 768-dimension Gemini embeddings for pgvector-backed search."""

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
        self.model: str = EMBEDDING_MODEL
        self.dimensions: int = EMBEDDING_DIMENSIONS
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("Gemini API key is not configured")

        if self._client is None:
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=int(self.timeout * 1000)),
            )
        return self._client

    async def embed_document(self, content: str) -> list[float]:
        """Embed document content for storage (RETRIEVAL_DOCUMENT)."""
        return await self._embed(content, "RETRIEVAL_DOCUMENT")

    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query (RETRIEVAL_QUERY)."""
        return await self._embed(query, "RETRIEVAL_QUERY")

    async def _embed(self, text: str, task_type: TaskType) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Text to embed must not be empty")

        client = self._get_client()
        start = time.perf_counter()

        try:
            response = await client.aio.models.embed_content(
                model=self.model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self.dimensions,
                ),
            )
        except errors.ClientError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            if exc.code == 429:
                logger.warning(
                    "provider=%s model=%s status=failure latency_ms=%.2f task_type=%s reason=rate_limit",
                    "gemini",
                    self.model,
                    latency_ms,
                    task_type,
                )
                raise LLMProviderError("Gemini rate limit exceeded", status_code=429) from exc
            logger.warning(
                "provider=%s model=%s status=failure latency_ms=%.2f task_type=%s reason=client_error upstream_status=%s",
                "gemini",
                self.model,
                latency_ms,
                task_type,
                exc.code,
            )
            raise LLMProviderError("Gemini embedding request failed", status_code=502) from exc
        except errors.ServerError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s model=%s status=failure latency_ms=%.2f task_type=%s reason=server_error upstream_status=%s",
                "gemini",
                self.model,
                latency_ms,
                task_type,
                exc.code,
            )
            raise LLMProviderError("Gemini service is unavailable", status_code=502) from exc
        except TimeoutError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s model=%s status=failure latency_ms=%.2f task_type=%s reason=timeout",
                "gemini",
                self.model,
                latency_ms,
                task_type,
            )
            raise LLMTimeoutError("Gemini embedding request timed out") from exc
        except errors.APIError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s model=%s status=failure latency_ms=%.2f task_type=%s reason=provider_error upstream_status=%s",
                "gemini",
                self.model,
                latency_ms,
                task_type,
                exc.code,
            )
            raise LLMProviderError("Gemini embedding request failed", status_code=502) from exc
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "provider=%s model=%s status=failure latency_ms=%.2f task_type=%s reason=unexpected",
                "gemini",
                self.model,
                latency_ms,
                task_type,
            )
            raise LLMProviderError("Gemini embedding request failed", status_code=502) from exc

        embedding = self._extract_embedding(response)
        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "provider=%s model=%s status=success latency_ms=%.2f task_type=%s dimensions=%d text_length=%d",
            "gemini",
            self.model,
            latency_ms,
            task_type,
            len(embedding),
            len(text),
        )
        return embedding

    def _extract_embedding(self, response: types.EmbedContentResponse) -> list[float]:
        embeddings = getattr(response, "embeddings", None)
        if not embeddings:
            logger.warning(
                "provider=%s model=%s status=failure reason=empty_response",
                "gemini",
                self.model,
            )
            raise LLMProviderError("Gemini returned no embeddings", status_code=502)

        values = getattr(embeddings[0], "values", None)
        if not values:
            logger.warning(
                "provider=%s model=%s status=failure reason=empty_embedding",
                "gemini",
                self.model,
            )
            raise LLMProviderError("Gemini returned an empty embedding", status_code=502)

        if len(values) != self.dimensions:
            logger.warning(
                "provider=%s model=%s status=failure reason=unexpected_dimensions dimensions=%d expected=%d",
                "gemini",
                self.model,
                len(values),
                self.dimensions,
            )
            raise LLMProviderError(
                f"Gemini returned {len(values)} dimensions, expected {self.dimensions}",
                status_code=502,
            )

        return [float(value) for value in values]
