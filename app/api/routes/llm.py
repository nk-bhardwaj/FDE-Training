from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.schemas.llm import LLMRequest, LLMResponse, TokenUsage
from app.services.llm_errors import (
    LLMProviderError,
    LLMTimeoutError,
    MissingAPIKeyError,
)
from app.services.llm_service import LLMService

logger = get_logger(__name__)

router = APIRouter()

llm_service = LLMService()


@router.post("/chat", response_model=LLMResponse)
async def generate_response(request: LLMRequest) -> LLMResponse:
    logger.info("Received chat request provider=%s", request.provider)
    try:
        response, model, latency_ms, usage = await llm_service.generate_response(
            provider=request.provider,
            prompt=request.prompt,
        )

        logger.info("Chat request completed provider=%s", request.provider)
        return LLMResponse(
            provider=request.provider,
            response=response,
            model=model,
            latency_ms=latency_ms,
            usage=TokenUsage(**(usage or {})),
        )

    except MissingAPIKeyError as exc:
        logger.warning(
            "LLM request failed provider=%s status=503 reason=missing_api_key",
            request.provider,
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMTimeoutError as exc:
        logger.warning(
            "LLM request failed provider=%s status=504 reason=timeout",
            request.provider,
        )
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except LLMProviderError as exc:
        logger.warning(
            "LLM request failed provider=%s status=%s reason=provider_error",
            request.provider,
            exc.status_code,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        logger.warning(
            "LLM request failed provider=%s status=400 reason=invalid_request",
            request.provider,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception(
            "LLM request failed provider=%s status=502 reason=unexpected",
            request.provider,
        )
        raise HTTPException(
            status_code=502,
            detail="LLM provider request failed",
        ) from None
