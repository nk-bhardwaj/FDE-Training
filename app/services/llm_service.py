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
    ) -> LLMGeneration:
        service = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "groq": self.groq,
        }.get(provider)
        if service is None:
            raise ValueError(f"Unsupported provider: {provider}")
        return await service.generate_response(prompt)
