from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://reelrecall:reelrecall@localhost:5432/reelrecall"
    jwt_secret: str = ""
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)
    data_dir: str = "dataset/media"
    ffmpeg_path: str = ""
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    transcription_model: str = ""
    vision_model: str = ""
    summary_model: str = ""
    summary_api_base: str = ""
    summary_api_key: str = ""
    ocr_languages: str = "en,hi"
    max_video_duration_seconds: int = Field(default=600, ge=1)
    max_video_size_mb: int = Field(default=250, ge=1)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )


settings = Settings()
