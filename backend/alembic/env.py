import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic can be launched from the project root or its Scripts entry point.
# Ensure imports resolve from the backend package in either case.
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.database import Base

from app.models.embedding import Embedding
from app.models.search_history import SearchHistory
from app.models.user import User
from app.models.video import Video
from app.models.video_content import VideoContent

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

_model_types = (
    Embedding,
    SearchHistory,
    User,
    Video,
    VideoContent,
)
target_metadata = Base.metadata
if any(model.__table__.metadata is not target_metadata for model in _model_types):
    raise RuntimeError("Alembic models must share the application metadata")


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
