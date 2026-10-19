from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import synonym

from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    source = Column(String, nullable=False)
    creator = Column(String, nullable=True)
    canonical_url = Column(String, nullable=True)
    external_video_id = Column(String, nullable=True, index=True)
    source_caption = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    thumbnail_url = Column(String, nullable=True)
    source_metadata = Column(JSON, nullable=False, default=dict)
    metadata_status = Column(String, nullable=False, default="pending")
    permission_status = Column(String, nullable=False, default="unknown")
    local_media_path = Column(Text, nullable=True)
    stage_statuses = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    manual_category = Column(String, nullable=True)
    manual_category_source = Column(String, nullable=True)
    curation_notes = Column(Text, nullable=True)
    curation_notes_source = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    visual_description = Column(Text, nullable=True)
    saved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    status = Column(String, nullable=False, default="pending")

    source_url = synonym("url")
    source_platform = synonym("source")
    creator_name = synonym("creator")
    duration_seconds = synonym("duration")
    indexing_status = synonym("status")

    duration = Column(Integer, nullable=True)
