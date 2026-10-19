from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import synonym

from app.core.database import Base


class VideoContent(Base):
    __tablename__ = "video_content"
    __table_args__ = (UniqueConstraint("video_id", "content_key", name="uq_video_content_key"),)

    id = Column(String, primary_key=True, index=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    content_type = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    source_type = Column(String, nullable=False, default="model_generated")
    source_field = Column(String, nullable=False)
    language = Column(String, nullable=True)
    timestamp_start = Column(Float, nullable=True)
    timestamp_end = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    model_name = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    processing_status = Column(String, nullable=False, default="completed")
    evidence = Column(JSON, nullable=False, default=list)
    content_key = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    content_text = synonym("text")
