from collections.abc import AsyncGenerator
from typing import Any

from app.schemas.llm import LLMGeneration
from app.services.anthropic_service import AnthropicService
from app.services.groq_service import GroqService
from app.services.openai_service import OpenAIService


class LLMService:
    def __init__(self) -> None:
        self.openai = OpenAIService()
        self.anthropic = AnthropicService()
        self.groq = GroqService()

    async def generate_response(
        self,
        provider: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMGeneration:
        service = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "groq": self.groq,
        }.get(provider)
        if service is None:
            raise ValueError(f"Unsupported provider: {provider}")
        return await service.generate_response(prompt, system_prompt=system_prompt)

    async def generate_stream(
        self,
        provider: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[tuple[str, dict[str, int | None] | None, str]]:
        """Stream response from the selected provider."""
        service = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "groq": self.groq,
        }.get(provider)
        if service is None:
            raise ValueError(f"Unsupported provider: {provider}")
        async for item in service.generate_stream(prompt, system_prompt=system_prompt):
            yield item

    async def generate_with_tools(
        self,
        provider: str,
        prompt: str,
        tool_definitions: dict[str, dict[str, Any]],
        system_prompt: str | None = None,
    ) -> LLMGeneration:
        service = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "groq": self.groq,
        }.get(provider)
        if service is None:
            raise ValueError(f"Unsupported provider: {provider}")
        return await service.generate_with_tools(
            prompt, tool_definitions, system_prompt=system_prompt
        )
