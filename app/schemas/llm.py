from typing import Literal

from pydantic import BaseModel, Field

ProviderName = Literal["openai", "anthropic", "groq"]
LLMGeneration = tuple[str, str, float, dict[str, int | None]]


class LLMRequest(BaseModel):
    provider: ProviderName
    prompt: str = Field(min_length=1, max_length=10000)


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class LLMResponse(BaseModel):
    provider: ProviderName
    response: str
    model: str
    latency_ms: float
    usage: TokenUsage | None = None
