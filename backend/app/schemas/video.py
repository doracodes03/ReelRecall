from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class VideoCreate(BaseModel):
    url: HttpUrl
    manual_category: str | None = Field(default=None, max_length=80)
    curation_notes: str | None = Field(default=None, max_length=2000)
    permission_status: Literal["unknown", "owned", "authorized"] = "unknown"


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    url: str
    canonical_url: str | None = None
    source: str
    external_video_id: str | None = None
    title: str | None = None
    source_caption: str | None = None
    creator: str | None = None
    duration: int | None = None
    thumbnail_url: str | None = None
    manual_category: str | None = None
    curation_notes: str | None = None
    permission_status: str
    status: str
    metadata_status: str
    stage_statuses: dict[str, str] = Field(default_factory=dict)
    saved_at: datetime


class BulkReindexRead(BaseModel):
    total_count: int
    queued_count: int
    already_active_count: int
    queued_video_ids: list[str] = Field(default_factory=list)


class ExtractedContentRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        protected_namespaces=(),
    )

    id: str
    content_type: str
    content_text: str = Field(validation_alias="text")
    source_type: str
    source_field: str
    language: str | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    confidence: float | None = None
    model_name: str | None = None
    model_version: str | None = None
    processing_status: str
