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
    ) -> str:
        if provider == "openai":
            return await self.openai.generate_response(prompt)

        if provider == "anthropic":
            return await self.anthropic.generate_response(prompt)

        if provider == "groq":
            return await self.groq.generate_response(prompt)

        raise ValueError(f"Unsupported provider: {provider}")
