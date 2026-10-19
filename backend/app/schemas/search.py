from typing import Literal

from pydantic import BaseModel, Field, field_validator


RetrievalMode = Literal["hybrid", "lexical", "semantic", "visual", "metadata"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    mode: RetrievalMode = "hybrid"
    benchmark: bool = True
    include_user_annotations: bool = False

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("Search query cannot be blank")
        return query


class SearchEvidence(BaseModel):
    source_type: str
    source_field: str
    excerpt: str
    timestamp_start: float | None = None


class SearchResult(BaseModel):
    video_id: str
    title: str
    score: float
    match_reason: str
    highlights: list[str]
    evidence: SearchEvidence
    channels: list[str]


class SearchResponse(BaseModel):
    query: str
    mode: RetrievalMode
    results: list[SearchResult]
    warnings: list[str]
    latency_ms: float
