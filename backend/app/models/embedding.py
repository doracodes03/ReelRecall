from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import synonym

from app.core.database import Base


class Embedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint(
            "content_record_id", "model", "modality",
            name="uq_embedding_content_model_modality",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    content_record_id = Column(
        String, ForeignKey("video_content.id"), nullable=True, index=True
    )
    modality = Column(String, nullable=False, default="text")
    source = Column(String, nullable=False)
    model = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    vector = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    model_name = synonym("model")
    embedding = synonym("vector")
