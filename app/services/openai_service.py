import os
import time
from collections.abc import AsyncGenerator
from typing import Any

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
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
from app.tools.orchestrator import (
    ToolCall,
    ToolTurn,
    run_tool_calling,
)

logger = get_logger(__name__)

load_dotenv()


class OpenAIService:
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
        self.model: str = "gpt-4o-mini"
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("OpenAI API key is not configured")

        if self._client is None:
            self._client = AsyncOpenAI(api_key=api_key, timeout=self.timeout)
        return self._client

    async def generate_response(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        system_prompt: str | None = None,
    ) -> LLMGeneration:
        client = self._get_client()
        start = time.perf_counter()

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            output_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None
            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
                "openai",
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
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI authentication failed", status_code=502) from exc
        except RateLimitError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=rate_limit",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI rate limit exceeded", status_code=429) from exc
        except (APITimeoutError, TimeoutError) as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=timeout",
                "openai",
                latency_ms,
            )
            raise LLMTimeoutError("OpenAI request timed out") from exc
        except APIConnectionError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=connection",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI service is unavailable", status_code=502) from exc
        except APIError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=provider_error",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI request failed", status_code=502) from exc
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "provider=%s status=failure latency_ms=%.2f reason=unexpected",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI request failed", status_code=502) from exc

    async def generate_stream(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        system_prompt: str | None = None,
    ) -> AsyncGenerator[tuple[str, dict[str, int | None] | None, str]]:
        """Stream response from OpenAI. Yields (chunk_text, usage_dict_or_None, model)."""
        client = self._get_client()
        start = time.perf_counter()
        accumulated_text = ""
        usage: dict[str, int | None] = {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    accumulated_text += content
                    yield content, None, model
                if chunk.usage is not None:
                    usage = {
                        "input_tokens": getattr(chunk.usage, "prompt_tokens", None),
                        "output_tokens": getattr(chunk.usage, "completion_tokens", None),
                        "total_tokens": getattr(chunk.usage, "total_tokens", None),
                    }
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f streaming_completed input_tokens=%s output_tokens=%s total_tokens=%s",
                "openai",
                model,
                latency_ms,
                usage["input_tokens"],
                usage["output_tokens"],
                usage["total_tokens"],
            )
            yield "", usage, model
        except AuthenticationError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=authentication",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI authentication failed", status_code=502) from exc
        except RateLimitError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=rate_limit",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI rate limit exceeded", status_code=429) from exc
        except (APITimeoutError, TimeoutError) as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=timeout",
                "openai",
                latency_ms,
            )
            raise LLMTimeoutError("OpenAI request timed out") from exc
        except APIConnectionError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=connection",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI service is unavailable", status_code=502) from exc
        except APIError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=provider_error",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI request failed", status_code=502) from exc
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "provider=%s status=failure latency_ms=%.2f reason=unexpected",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI request failed", status_code=502) from exc

    @property
    def provider_name(self) -> str:
        return "openai"

    def format_tools(self, tool_definitions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": definition.get("name") or key,
                    "description": definition.get("description") or "",
                    "parameters": definition.get("parameters")
                    or {
                        "type": "object",
                        "properties": {},
                    },
                },
            }
            for key, definition in tool_definitions.items()
        ]

    async def send_tool_request(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
    ) -> ToolTurn:
        client = self._get_client()
        start = time.perf_counter()
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            output_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            message = response.choices[0].message
            content = message.content or ""

            tool_calls: list[ToolCall] = []
            for tool_call in message.tool_calls or []:
                tool_calls.append(
                    ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=tool_call.function.arguments or "{}",
                    )
                )

            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
                "openai",
                model,
                latency_ms,
                input_tokens,
                output_tokens,
                total_tokens,
            )
            return ToolTurn(
                content=content,
                tool_calls=tool_calls,
                usage={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                },
            )
        except AuthenticationError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=authentication",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI authentication failed", status_code=502) from exc
        except RateLimitError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=rate_limit",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI rate limit exceeded", status_code=429) from exc
        except (APITimeoutError, TimeoutError) as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=timeout",
                "openai",
                latency_ms,
            )
            raise LLMTimeoutError("OpenAI request timed out") from exc
        except APIConnectionError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=connection",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI service is unavailable", status_code=502) from exc
        except APIError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "provider=%s status=failure latency_ms=%.2f reason=provider_error",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI request failed", status_code=502) from exc
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "provider=%s status=failure latency_ms=%.2f reason=unexpected",
                "openai",
                latency_ms,
            )
            raise LLMProviderError("OpenAI request failed", status_code=502) from exc

    def append_assistant_message(self, messages: list[dict[str, Any]], turn: ToolTurn) -> None:
        message: dict[str, Any] = {"role": "assistant", "content": turn.content or ""}
        if turn.tool_calls:
            message["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    },
                }
                for tool_call in turn.tool_calls
            ]
        messages.append(message)

    def append_tool_result(
        self, messages: list[dict[str, Any]], tool_call: ToolCall, content: str
    ) -> None:
        messages.append(
            {
                "role": "tool",
                "content": content,
                "tool_call_id": tool_call.id,
            }
        )

    async def generate_with_tools(
        self,
        prompt: str,
        tool_definitions: dict[str, dict[str, Any]],
        system_prompt: str | None = None,
    ) -> LLMGeneration:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await run_tool_calling(self, messages, tool_definitions, model=self.model)
