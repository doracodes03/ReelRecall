"""Add provenance-aware multimodal indexing tables and legacy-safe columns."""

from alembic import op
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    inspect,
    text,
)

from app.core.database import Base

# Import all model classes so create_all also creates new tables on legacy databases.
from app.models.embedding import Embedding
from app.models.search_history import SearchHistory
from app.models.user import User
from app.models.video import Video
from app.models.video_content import VideoContent

_model_types = (
    Embedding,
    SearchHistory,
    User,
    Video,
    VideoContent,
)
if any(model.__table__.metadata is not Base.metadata for model in _model_types):
    raise RuntimeError("Migration models must share the application metadata")

revision = "20260814_provenance_indexing"
down_revision = None
branch_labels = None
depends_on = None


def _ensure_column(table_name: str, column: Column) -> None:
    inspector = inspect(op.get_bind())
    present = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in present:
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)

    _ensure_column("users", Column("hashed_password", String(), nullable=False, server_default=""))
    _ensure_column("videos", Column("user_id", String(), nullable=True))
    _ensure_column("videos", Column("canonical_url", String(), nullable=True))
    _ensure_column("videos", Column("external_video_id", String(), nullable=True))
    _ensure_column("videos", Column("source_caption", Text(), nullable=True))
    _ensure_column("videos", Column("published_at", DateTime(timezone=True), nullable=True))
    _ensure_column("videos", Column("thumbnail_url", String(), nullable=True))
    _ensure_column(
        "videos",
        Column(
            "source_metadata",
            JSON(),
            nullable=False,
            server_default=text("'{}'"),
        ),
    )
    _ensure_column(
        "videos",
        Column("metadata_status", String(), nullable=False, server_default="pending"),
    )
    _ensure_column(
        "videos",
        Column(
            "permission_status",
            String(),
            nullable=False,
            server_default="unknown",
        ),
    )
    _ensure_column("videos", Column("local_media_path", Text(), nullable=True))
    _ensure_column(
        "videos",
        Column(
            "stage_statuses",
            JSON(),
            nullable=False,
            server_default=text("'{}'"),
        ),
    )
    _ensure_column("videos", Column("manual_category", String(), nullable=True))
    _ensure_column(
        "videos", Column("manual_category_source", String(), nullable=True)
    )
    _ensure_column("videos", Column("curation_notes", Text(), nullable=True))
    _ensure_column(
        "videos", Column("curation_notes_source", String(), nullable=True)
    )
    _ensure_column("videos", Column("duration", Integer(), nullable=True))
    _ensure_column(
        "videos",
        Column("status", String(), nullable=False, server_default="pending"),
    )

    op.create_index(
        "ix_videos_user_id",
        "videos",
        ["user_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_videos_user_id", table_name="videos", if_exists=True)
    # This migration is additive because the pre-existing videos table may hold
    # user data; downgrade deliberately does not drop tables or legacy columns.
