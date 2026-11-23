"""API routes for RAG question answering."""

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.schemas.rag_request import RAGAnswerApiResponse, RAGRequest
from app.services.document_service import DatabaseNotConfiguredError, DocumentStoreError
from app.services.llm_errors import LLMProviderError, LLMTimeoutError, MissingAPIKeyError
from app.services.rag_pipeline_service import (
    RAGPipelineConfig,
    RAGPipelineError,
    RAGPipelineService,
)

logger = get_logger(__name__)

router = APIRouter()

rag_pipeline_service = RAGPipelineService()


@router.post("/answer", response_model=RAGAnswerApiResponse)
async def answer(request: RAGRequest) -> RAGAnswerApiResponse:
    """Generate a grounded answer using retrieval + rerank + context + answer."""
    logger.info(
        "Received RAG answer request provider=%s top_k=%d has_filters=%s",
        request.provider,
        request.top_k,
        request.metadata_filters is not None,
    )

    try:
        config = RAGPipelineConfig(retrieval_top_k=request.top_k)
        result = await rag_pipeline_service.run(
            question=request.question,
            provider=request.provider,
            config=config,
            metadata_filters=request.metadata_filters,
        )
        return RAGAnswerApiResponse(
            answer=result.answer.answer,
            citations=result.answer.citations,
            abstained=result.answer.abstained,
            provider=result.answer.provider,
            model=result.answer.model,
            latency_ms=result.answer.latency_ms,
            usage=result.answer.usage,
            context_chunks=result.answer.context_chunks,
            context_tokens=result.answer.context_tokens,
            retrieval_top_k=result.config_used.retrieval_top_k,
            retrieval_candidate_pool=result.config_used.retrieval_candidate_pool,
            rerank_enabled=result.config_used.rerank_enabled,
            rerank_top_k=result.config_used.rerank_top_k,
            context_max_tokens=result.config_used.context_max_tokens,
        )
    except MissingAPIKeyError as exc:
        logger.warning(
            "RAG answer failed provider=%s status=503 reason=missing_api_key", request.provider
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DatabaseNotConfiguredError as exc:
        logger.warning("RAG answer failed status=503 reason=database_not_configured")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMTimeoutError as exc:
        logger.warning("RAG answer failed provider=%s status=504 reason=timeout", request.provider)
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except LLMProviderError as exc:
        logger.warning(
            "RAG answer failed provider=%s status=%s reason=provider_error",
            request.provider,
            exc.status_code,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except RAGPipelineError as exc:
        logger.warning(
            "RAG answer failed provider=%s status=%s reason=pipeline_error step=%s",
            request.provider,
            exc.status_code,
            exc.step,
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"{exc} (step={exc.step})",
        ) from exc
    except DocumentStoreError as exc:
        logger.warning("RAG answer failed status=502 reason=database_error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        logger.warning("RAG answer failed status=400 reason=invalid_request")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception(
            "RAG answer failed provider=%s status=502 reason=unexpected", request.provider
        )
        raise HTTPException(status_code=502, detail="RAG answer request failed") from None
