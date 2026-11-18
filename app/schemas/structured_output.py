from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.llm import ProviderName


class SupportAnalysis(BaseModel):
    category: str = Field(min_length=1)
    sentiment: Literal["positive", "negative", "neutral"]
    summary: str = Field(min_length=1)
    suggested_resolution: str = Field(min_length=1)
    requires_human: bool


class StructuredChatRequest(BaseModel):
    provider: ProviderName
    message: str = Field(min_length=1, max_length=10000)


class StructuredChatResponse(BaseModel):
    provider: ProviderName
    analysis: SupportAnalysis
    model: str
    latency_ms: float
    usage: dict | None = None
    attempts: int
