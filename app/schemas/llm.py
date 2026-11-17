from typing import Literal

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    provider: Literal["openai", "anthropic", "groq"]
    prompt: str = Field(min_length=1, max_length=10000)


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class LLMResponse(BaseModel):
    provider: str
    response: str
    model: str
    latency_ms: float
    usage: TokenUsage | None = None
