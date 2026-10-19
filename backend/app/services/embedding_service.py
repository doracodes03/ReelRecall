import importlib.metadata
import json
import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)
ALLOWED_CONTENT_TYPES = {
    "transcript",
    "translation",
    "ocr",
    "visual_description",
    "summary",
    "entity",
    "topic",
}
ALLOWED_SOURCE_TYPES = {"audio", "video_frame", "model_generated"}
ALLOWED_SOURCE_FIELDS = {
    "original_transcript": "transcript",
    "translated_transcript": "translation",
    "frame_ocr": "ocr",
    "visual_frame_description": "visual_description",
    "evidence_summary": "summary",
    "evidence_concept": "entity",
    "evidence_topic": "topic",
}


def is_searchable_content(record: Any) -> bool:
    content_type = _field(record, "content_type")
    source_type = _field(record, "source_type")
    source_field = _field(record, "source_field")
    status = _field(record, "processing_status")
    text = _field(record, "text")
    return bool(
        content_type in ALLOWED_CONTENT_TYPES
        and source_type in ALLOWED_SOURCE_TYPES
        and ALLOWED_SOURCE_FIELDS.get(source_field) == content_type
        and status == "completed"
        and isinstance(text, str)
        and text.strip()
    )


def build_embedding_inputs(
    video: Any,
    content_records: list[Any],
    include_translations: bool = True,
) -> list[dict[str, str]]:
    """Select explicit evidence fields; annotations and evaluation labels are never inputs."""
    inputs: list[dict[str, str]] = []
    title = _field(video, "title")
    caption = _field(video, "source_caption")
    if title and title.strip():
        inputs.append({"source_field": "title", "text": title.strip()})
    if caption and caption.strip():
        inputs.append({"source_field": "source_caption", "text": caption.strip()})

    for record in content_records:
        if not is_searchable_content(record):
            continue
        content_type = _field(record, "content_type")
        if content_type == "translation" and not include_translations:
            continue
        source_field = _field(record, "source_field")
        text = _field(record, "text")
        content_record_id = _field(record, "id")
        embedding_input = {
            "source_field": source_field,
            "text": text.strip(),
        }
        if content_record_id is not None:
            embedding_input["content_record_id"] = str(content_record_id)
        inputs.append(
            embedding_input
        )
    return inputs


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


class EmbeddingUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> tuple[Any, str]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingUnavailable(
            "sentence-transformers is required for the configured embedding model"
        ) from exc
    model = SentenceTransformer(model_name)
    try:
        version = importlib.metadata.version("sentence-transformers")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return model, version


class EmbeddingService:
    """Optional multilingual SentenceTransformer provider; no fabricated vector fallback."""

    def __init__(self) -> None:
        self.model_name = settings.embedding_model.strip()
        self._model: Any = None
        self._version: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.model_name)

    @property
    def model_version(self) -> str | None:
        return self._version

    def embed(self, value: str) -> list[float]:
        if not self.model_name:
            raise EmbeddingUnavailable(
                "No embedding model configured; set EMBEDDING_MODEL to enable semantic search"
            )
        if self._model is None:
            try:
                self._model, self._version = _load_model(self.model_name)
            except (ImportError, OSError, RuntimeError, ValueError) as exc:
                raise EmbeddingUnavailable(
                    f"Unable to load embedding model {self.model_name!r}: {exc}"
                ) from exc
        try:
            vector = self._model.encode(value, normalize_embeddings=True)
        except (OSError, RuntimeError, ValueError) as exc:
            raise EmbeddingUnavailable(f"Embedding failed: {exc}") from exc
        return [float(component) for component in vector]

    def serialize(self, vector: list[float]) -> str:
        return json.dumps(vector, separators=(",", ":"))

    @staticmethod
    def cosine_similarity(left: list[float], right: list[float]) -> float:
        if len(left) != len(right) or not left:
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sum(a * a for a in left) ** 0.5
        right_norm = sum(b * b for b in right) ** 0.5
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)
