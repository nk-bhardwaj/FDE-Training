import json
import os
import time
from collections.abc import AsyncGenerator
from typing import Any

from anthropic import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from anthropic.types import Message
from dotenv import load_dotenv

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


class AnthropicService:
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
        self.model: str = "claude-sonnet-4-5"
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
        system_prompt: str | None = None,
    ) -> LLMGeneration:
        client = self._get_client()
        start = time.perf_counter()

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=messages,
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

    async def generate_stream(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-5",
        system_prompt: str | None = None,
    ) -> AsyncGenerator[tuple[str, dict[str, int | None] | None, str]]:
        """Stream response from Anthropic. Yields (chunk_text, usage_dict_or_None, model)."""
        client = self._get_client()
        start = time.perf_counter()
        accumulated_text = ""

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with client.messages.stream(
                model=model,
                max_tokens=1024,
                system=system_prompt if system_prompt else None,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    accumulated_text += text
                    yield text, None, model
            latency_ms = (time.perf_counter() - start) * 1000
            final_message = stream.get_final_message()
            final_usage = getattr(final_message, "usage", None)
            input_tokens = getattr(final_usage, "input_tokens", None) if final_usage else None
            output_tokens = getattr(final_usage, "output_tokens", None) if final_usage else None
            total_tokens = getattr(final_usage, "total_tokens", None) if final_usage else None
            if total_tokens is None and input_tokens is not None and output_tokens is not None:
                total_tokens = input_tokens + output_tokens
            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }
            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f streaming_completed input_tokens=%s output_tokens=%s total_tokens=%s",
                "anthropic",
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

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def format_tools(self, tool_definitions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": definition.get("name") or key,
                "description": definition.get("description") or "",
                "input_schema": definition.get("parameters")
                or {
                    "type": "object",
                    "properties": {},
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
            response: Message = await client.messages.create(
                model=model,
                max_tokens=1024,
                messages=messages,
                tools=tools,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "input_tokens", None) if usage else None
            output_tokens = getattr(usage, "output_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None
            if total_tokens is None and input_tokens is not None and output_tokens is not None:
                total_tokens = input_tokens + output_tokens
            usage_dict = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }

            content = ""
            tool_calls: list[ToolCall] = []
            for block in response.content or []:
                block_type = getattr(block, "type", None)
                if block_type == "text":
                    content = content + (getattr(block, "text", "") or "")
                elif block_type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=json.dumps(block.input or {}),
                        )
                    )

            logger.info(
                "provider=%s model=%s status=success latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
                "anthropic",
                model,
                latency_ms,
                usage_dict["input_tokens"],
                usage_dict["output_tokens"],
                usage_dict["total_tokens"],
            )
            return ToolTurn(
                content=content,
                tool_calls=tool_calls,
                usage=usage_dict,
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

    def append_assistant_message(self, messages: list[dict[str, Any]], turn: ToolTurn) -> None:
        content: list[dict[str, Any]] = []
        if turn.content:
            content.append({"type": "text", "text": turn.content})
        for tool_call in turn.tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "input": json.loads(tool_call.arguments) if tool_call.arguments else {},
                }
            )
        messages.append({"role": "assistant", "content": content or ""})

    def append_tool_result(
        self, messages: list[dict[str, Any]], tool_call: ToolCall, content: str
    ) -> None:
        tool_result = {
            "type": "tool_result",
            "tool_use_id": tool_call.id,
            "content": content,
        }
        if (
            messages
            and messages[-1].get("role") == "user"
            and isinstance(messages[-1].get("content"), list)
        ):
            messages[-1]["content"].append(tool_result)
        else:
            messages.append(
                {
                    "role": "user",
                    "content": [tool_result],
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
