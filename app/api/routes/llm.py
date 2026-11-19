import json
import os
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.logging import get_logger
from app.schemas.llm import LLMRequest, LLMResponse, LLMToolRequest, TokenUsage
from app.schemas.structured_output import (
    StructuredChatRequest,
    StructuredChatResponse,
)
from app.services.llm_errors import (
    LLMProviderError,
    LLMTimeoutError,
    MissingAPIKeyError,
)
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptNotFoundError, PromptService
from app.services.structured_output_service import (
    StructuredOutputError,
    StructuredOutputService,
)

logger = get_logger(__name__)

router = APIRouter()

llm_service = LLMService()
structured_output_service = StructuredOutputService()

PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}


@router.post("/chat", response_model=LLMResponse)
async def generate_response(request: LLMRequest) -> LLMResponse:
    logger.info("Received chat request provider=%s", request.provider)
    try:
        system_prompt: str | None = None
        if request.prompt_version:
            prompt_service = PromptService()
            system_prompt = prompt_service.load_prompt(request.prompt_version)
            logger.info(
                "Prompt version %s loaded for provider %s", request.prompt_version, request.provider
            )

        response, model, latency_ms, usage = await llm_service.generate_response(
            provider=request.provider,
            prompt=request.prompt,
            system_prompt=system_prompt,
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
    except PromptNotFoundError as exc:
        logger.warning(
            "Prompt file not found provider=%s version=%s",
            request.provider,
            request.prompt_version,
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


@router.post("/chat/structured", response_model=StructuredChatResponse)
async def structured_chat(request: StructuredChatRequest) -> StructuredChatResponse:
    logger.info("Received structured chat request provider=%s", request.provider)
    try:
        result = await structured_output_service.analyze_support(
            provider=request.provider,
            message=request.message,
        )
        logger.info("Structured chat completed provider=%s", request.provider)
        return result

    except StructuredOutputError as exc:
        logger.warning(
            "Structured output failed provider=%s reason=%s",
            request.provider,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MissingAPIKeyError as exc:
        logger.warning(
            "Structured request failed provider=%s status=503 reason=missing_api_key",
            request.provider,
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMTimeoutError as exc:
        logger.warning(
            "Structured request failed provider=%s status=504 reason=timeout",
            request.provider,
        )
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except LLMProviderError as exc:
        logger.warning(
            "Structured request failed provider=%s status=%s reason=provider_error",
            request.provider,
            exc.status_code,
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        logger.warning(
            "Structured request failed provider=%s status=400 reason=invalid_request",
            request.provider,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception(
            "Structured request failed provider=%s status=502 reason=unexpected",
            request.provider,
        )
        raise HTTPException(
            status_code=502,
            detail="LLM provider request failed",
        ) from None


@router.post("/chat/stream")
async def stream_chat(request: LLMRequest, http_request: Request) -> StreamingResponse:
    logger.info("Received chat stream request provider=%s", request.provider)

    service = {
        "openai": llm_service.openai,
        "anthropic": llm_service.anthropic,
        "groq": llm_service.groq,
    }.get(request.provider)
    if service is None:
        logger.warning(
            "Stream request failed provider=%s status=400 reason=invalid_provider",
            request.provider,
        )
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")

    env_var = PROVIDER_API_KEY_ENV.get(request.provider)
    if not env_var or not os.getenv(env_var):
        logger.warning(
            "Stream request failed provider=%s status=503 reason=missing_api_key",
            request.provider,
        )
        raise HTTPException(status_code=503, detail=f"{request.provider} API key is not configured")

    system_prompt: str | None = None
    if request.prompt_version:
        prompt_service = PromptService()
        try:
            system_prompt = prompt_service.load_prompt(request.prompt_version)
        except PromptNotFoundError as exc:
            logger.warning(
                "Stream prompt file not found provider=%s version=%s",
                request.provider,
                request.prompt_version,
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def event_generator() -> AsyncGenerator[str]:
        start = time.perf_counter()
        model: str | None = None
        usage: dict[str, int | None] | None = None
        stream = None
        try:
            stream = llm_service.generate_stream(
                provider=request.provider,
                prompt=request.prompt,
                system_prompt=system_prompt,
            )
            async for text, chunk_usage, chunk_model in stream:
                if await http_request.is_disconnected():
                    logger.info("Client disconnected during stream provider=%s", request.provider)
                    return
                model = chunk_model
                usage = chunk_usage
                if text:
                    yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"
            latency_ms = (time.perf_counter() - start) * 1000
            yield f"data: {json.dumps({'type': 'done', 'model': model, 'latency_ms': latency_ms, 'usage': usage})}\n\n"
        except MissingAPIKeyError as exc:
            logger.warning(
                "Stream request failed provider=%s reason=missing_api_key", request.provider
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except LLMTimeoutError as exc:
            logger.warning("Stream request failed provider=%s reason=timeout", request.provider)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except LLMProviderError as exc:
            logger.warning(
                "Stream request failed provider=%s reason=provider_error", request.provider
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except ValueError as exc:
            logger.warning(
                "Stream request failed provider=%s reason=invalid_request", request.provider
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except Exception:
            logger.exception("Stream failed provider=%s", request.provider)
            yield f"data: {json.dumps({'type': 'error', 'message': 'LLM provider request failed'})}\n\n"
        finally:
            if stream is not None:
                await stream.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/tools", response_model=LLMResponse)
async def chat_tools(request: LLMToolRequest) -> LLMResponse:
    logger.info("Received chat tools request provider=%s", request.provider)
    try:
        from app.tools.order_tools import TOOL_DEFINITIONS

        tool_definitions = TOOL_DEFINITIONS

        response, model, latency_ms, usage = await llm_service.generate_with_tools(
            provider=request.provider,
            prompt=request.prompt,
            tool_definitions=tool_definitions,
            system_prompt=request.system_prompt,
        )

        logger.info("Chat tools request completed provider=%s", request.provider)
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
