"""Pydantic schemas for document semantic search API."""

from datetime import datetime

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=100)
    metadata_filters: dict[str, str | int | bool] | None = None


class SearchResultResponse(BaseModel):
    """A single semantic search result."""

    id: int
    content: str
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    similarity: float


class SemanticSearchResponse(BaseModel):
    """Response body for semantic search."""

    query: str
    results: list[SearchResultResponse]
    total_results: int
