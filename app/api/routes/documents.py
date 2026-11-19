"""API routes for document semantic search."""

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.schemas.documents import (
    SearchResultResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services.document_service import (
    DatabaseNotConfiguredError,
    DocumentService,
    DocumentStoreError,
)
from app.services.llm_errors import LLMProviderError, LLMTimeoutError, MissingAPIKeyError

logger = get_logger(__name__)

router = APIRouter()

document_service = DocumentService()


@router.post("/search", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest) -> SemanticSearchResponse:
    """Perform semantic search on stored documents."""
    logger.info(
        "Received semantic search request query_length=%d limit=%d",
        len(request.query),
        request.limit,
    )

    try:
        results = await document_service.semantic_search(
            query=request.query,
            limit=request.limit,
            metadata_filters=request.metadata_filters,
        )

        logger.info("Semantic search completed results=%d", len(results))
        return SemanticSearchResponse(
            query=request.query,
            results=[
                SearchResultResponse(
                    id=result.id,
                    content=result.content,
                    metadata=result.metadata,
                    created_at=result.created_at,
                    similarity=result.similarity,
                )
                for result in results
            ],
            total_results=len(results),
        )

    except MissingAPIKeyError as exc:
        logger.warning("Semantic search failed status=503 reason=missing_api_key")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMTimeoutError as exc:
        logger.warning("Semantic search failed status=504 reason=timeout")
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except LLMProviderError as exc:
        logger.warning("Semantic search failed status=%s reason=provider_error", exc.status_code)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except DatabaseNotConfiguredError as exc:
        logger.warning("Semantic search failed status=503 reason=database_not_configured")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DocumentStoreError as exc:
        logger.warning("Semantic search failed status=502 reason=database_error")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        logger.warning("Semantic search failed status=400 reason=invalid_request")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Semantic search failed status=502 reason=unexpected")
        raise HTTPException(status_code=502, detail="Semantic search request failed") from None
