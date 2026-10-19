from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.embedding import Embedding
from app.models.video import Video
from app.models.video_content import VideoContent
from app.services.embedding_service import EmbeddingService, build_embedding_inputs
from app.services.metadata_service import MetadataService
from app.services.ocr_service import OCRService
from app.services.summary_service import SummaryService
from app.services.transcript_service import TranscriptService
from app.services.visual_service import VisualService

logger = logging.getLogger(__name__)


def _stable_content_key(
    content_type: str,
    source_field: str,
    text: str,
    timestamp_start: float | None,
) -> str:
    stable = "\0".join(
        (
            content_type,
            source_field,
            f"{timestamp_start:.3f}" if timestamp_start is not None else "",
            text.strip(),
        )
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _upsert_content(
    session: Session,
    video: Video,
    *,
    content_type: str,
    content_text: str,
    source_type: str,
    source_field: str,
    language: str | None = None,
    timestamp_start: float | None = None,
    timestamp_end: float | None = None,
    confidence: float | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> VideoContent:
    key = _stable_content_key(
        content_type, source_field, content_text, timestamp_start
    )
    record = (
        session.query(VideoContent)
        .filter_by(video_id=video.id, content_key=key)
        .one_or_none()
    )
    if record is None:
        record = VideoContent(
            id=str(uuid.uuid4()),
            video_id=video.id,
            content_key=key,
        )
        session.add(record)
    record.content_type = content_type
    record.text = content_text.strip()
    record.source_type = source_type
    record.source_field = source_field
    record.language = language
    record.timestamp_start = timestamp_start
    record.timestamp_end = timestamp_end
    record.confidence = confidence
    record.model_name = model_name
    record.model_version = model_version
    record.processing_status = "completed"
    record.evidence = evidence or []
    return record


def _supersede_stale_content(
    session: Session,
    video_id: str,
    content_types: tuple[str, ...],
    current_records: list[VideoContent],
) -> None:
    current_ids = {
        record.id for record in current_records if record.content_type in content_types
    }
    query = session.query(VideoContent).filter(
        VideoContent.video_id == video_id,
        VideoContent.content_type.in_(content_types),
        VideoContent.processing_status == "completed",
    )
    if current_ids:
        query = query.filter(~VideoContent.id.in_(current_ids))
    for record in query.all():
        record.processing_status = "superseded"


class IndexingService:
    def __init__(
        self,
        metadata_service: MetadataService | None = None,
        transcript_service: TranscriptService | None = None,
        ocr_service: OCRService | None = None,
        visual_service: VisualService | None = None,
        summary_service: SummaryService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.metadata_service = metadata_service or MetadataService()
        self.transcript_service = transcript_service or TranscriptService()
        self.ocr_service = ocr_service or OCRService()
        self.visual_service = visual_service or VisualService()
        self.summary_service = summary_service or SummaryService()
        self.embedding_service = embedding_service or EmbeddingService()

    def process(self, session: Session, video_id: str) -> Video:
        video = session.query(Video).filter_by(id=video_id).one()
        video.status = "processing"
        video.stage_statuses = dict(video.stage_statuses or {})
        video.stage_statuses["indexing"] = "processing"
        video.updated_at = datetime.now(timezone.utc)
        session.commit()

        info: dict[str, Any] = {}
        try:
            info = self.metadata_service.extract(video.url)
            fields = self.metadata_service.source_fields(info)
            video.title = fields.get("title") or ""
            video.source_caption = fields.get("source_caption")
            video.creator = fields.get("creator")
            duration = fields.get("duration")
            video.duration = int(duration) if duration is not None else None
            video.thumbnail_url = fields.get("thumbnail_url")
            published = fields.get("published_at")
            video.published_at = (
                datetime.strptime(published, "%Y%m%d").replace(tzinfo=timezone.utc)
                if published
                else None
            )
            video.external_video_id = str(info.get("id") or video.external_video_id or "")
            video.source_metadata = {
                **(video.source_metadata or {}),
                "tags": fields.get("tags") or [],
                "extractor": fields.get("extractor"),
                "provenance": {
                    "title": "platform",
                    "source_caption": "platform",
                    "creator": "platform",
                    "duration": "platform",
                    "thumbnail_url": "platform",
                    "published_at": "platform",
                    "tags": "platform",
                },
            }
            video.metadata_status = "retrieved"
            video.stage_statuses["metadata"] = "completed"
        except Exception as exc:
            logger.warning("Metadata retrieval failed for video %s: %s", video_id, exc)
            video.metadata_status = "failed"
            video.stage_statuses["metadata"] = f"failed: {type(exc).__name__}: {exc}"

        media_path = self._resolve_media_path(video)
        if (
            video.duration is not None
            and video.duration > settings.max_video_duration_seconds
        ):
            media_path = None
            video.stage_statuses["media"] = (
                "skipped: duration exceeds configured limit"
            )
        elif media_path is None and video.permission_status in {"owned", "authorized"}:
            if not info:
                video.stage_statuses["media"] = "failed: metadata unavailable"
            else:
                try:
                    downloaded = self.metadata_service.download(
                        video.url, video.external_video_id or str(info["id"])
                    )
                    media_path = downloaded
                    video.local_media_path = str(downloaded)
                    video.stage_statuses["media"] = "completed"
                except Exception as exc:
                    logger.warning("Media download failed for video %s: %s", video_id, exc)
                    video.stage_statuses["media"] = (
                        f"failed: {type(exc).__name__}: {exc}"
                    )
        elif media_path:
            video.stage_statuses["media"] = "completed"
        else:
            video.stage_statuses["media"] = "skipped: permission not confirmed"

        session.flush()
        content_records: list[VideoContent] = []
        if media_path:
            self._extract_transcript(session, video, media_path, content_records)
            if video.stage_statuses["transcript"] in {"completed", "empty"}:
                _supersede_stale_content(
                    session, video.id, ("transcript", "translation"), content_records
                )
            self._extract_ocr(session, video, media_path, content_records)
            if video.stage_statuses["ocr"] in {"completed", "empty"}:
                _supersede_stale_content(
                    session, video.id, ("ocr",), content_records
                )
            self._extract_visual(session, video, media_path, content_records)
            if video.stage_statuses["visual"] in {"completed", "empty"}:
                _supersede_stale_content(
                    session, video.id, ("visual_description",), content_records
                )
            self._summarize(session, video, content_records)
            if video.stage_statuses["summary"] == "completed":
                _supersede_stale_content(
                    session, video.id, ("summary", "entity", "topic"), content_records
                )
        else:
            for stage in ("transcript", "ocr", "visual", "summary"):
                video.stage_statuses[stage] = "skipped: media unavailable"
        session.flush()
        active_content_records = (
            session.query(VideoContent)
            .filter_by(video_id=video.id, processing_status="completed")
            .all()
        )
        active_ids = [record.id for record in active_content_records]
        stale_embedding_query = session.query(Embedding).filter(
            Embedding.video_id == video.id,
            Embedding.content_record_id.isnot(None),
            ~Embedding.content_record_id.in_(active_ids),
        )
        stale_embedding_query.delete(synchronize_session=False)
        self._embed(session, video, active_content_records)

        extracted = active_content_records
        stage_failures = any(
            status.startswith(("failed", "unsupported"))
            for status in video.stage_statuses.values()
        )
        if extracted:
            video.status = "partial" if stage_failures else "indexed"
        elif video.metadata_status == "retrieved":
            video.status = "metadata_only"
        else:
            video.status = "failed"
        video.stage_statuses["indexing"] = "completed"
        video.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(video)
        return video

    @staticmethod
    def _resolve_media_path(video: Video) -> Path | None:
        if not video.local_media_path:
            return None
        candidate = Path(video.local_media_path)
        if not candidate.is_absolute():
            candidate = Path(__file__).resolve().parents[3] / candidate
        if candidate.is_file():
            return candidate.resolve()
        return None

    def _extract_transcript(
        self,
        session: Session,
        video: Video,
        media_path: Path,
        records: list[VideoContent],
    ) -> None:
        try:
            result = self.transcript_service.transcribe(media_path)
            video.stage_statuses["transcript"] = result["status"]
            for segment in result.get("segments", []):
                records.append(
                    _upsert_content(
                        session,
                        video,
                        content_type="transcript",
                        content_text=segment["text"],
                        source_type="audio",
                        source_field="original_transcript",
                        language=segment.get("language") or result.get("language"),
                        timestamp_start=segment.get("start"),
                        timestamp_end=segment.get("end"),
                        confidence=segment.get("confidence"),
                        model_name=settings.transcription_model or None,
                        model_version=result.get("model_version"),
                    )
                )
        except Exception as exc:
            logger.exception("Transcription failed for video %s", video.id)
            video.stage_statuses["transcript"] = (
                f"failed: {type(exc).__name__}: {exc}"
            )

    def _extract_ocr(
        self,
        session: Session,
        video: Video,
        media_path: Path,
        records: list[VideoContent],
    ) -> None:
        try:
            result = self.ocr_service.extract(media_path)
            video.stage_statuses["ocr"] = result["status"]
            for item in result.get("items", []):
                records.append(
                    _upsert_content(
                        session,
                        video,
                        content_type="ocr",
                        content_text=item["text"],
                        source_type="video_frame",
                        source_field="frame_ocr",
                        language=item.get("language"),
                        timestamp_start=item.get("timestamp"),
                        confidence=item.get("confidence"),
                        model_name="easyocr",
                        model_version=item.get("model_version"),
                    )
                )
        except Exception as exc:
            logger.exception("OCR failed for video %s", video.id)
            video.stage_statuses["ocr"] = f"failed: {type(exc).__name__}: {exc}"

    def _extract_visual(
        self,
        session: Session,
        video: Video,
        media_path: Path,
        records: list[VideoContent],
    ) -> None:
        try:
            result = self.visual_service.describe_frames(media_path)
            video.stage_statuses["visual"] = result["status"]
            for item in result.get("items", []):
                records.append(
                    _upsert_content(
                        session,
                        video,
                        content_type="visual_description",
                        content_text=item["text"],
                        source_type="video_frame",
                        source_field="visual_frame_description",
                        timestamp_start=item.get("timestamp"),
                        model_name=settings.vision_model or None,
                        model_version=item.get("model_version"),
                    )
                )
        except Exception as exc:
            logger.exception("Visual analysis failed for video %s", video.id)
            video.stage_statuses["visual"] = (
                f"failed: {type(exc).__name__}: {exc}"
            )

    def _summarize(
        self,
        session: Session,
        video: Video,
        records: list[VideoContent],
    ) -> None:
        evidence = [
            {
                "id": item.id,
                "source_field": item.source_field,
                "text": item.text,
                "timestamp_start": item.timestamp_start,
                "confidence": item.confidence,
            }
            for item in records
            if item.content_type
            in {"transcript", "ocr", "visual_description", "translation"}
        ]
        metadata = {
            "title": video.title,
            "source_caption": video.source_caption,
        }
        try:
            result = self.summary_service.summarize(metadata, evidence)
            if result is None:
                video.stage_statuses["summary"] = "unsupported: no summary provider configured"
                return
            summary_evidence = [
                {"content_record_id": evidence_id}
                for evidence_id in result["summary_evidence_ids"]
            ]
            records.append(
                _upsert_content(
                    session,
                    video,
                    content_type="summary",
                    content_text=result["summary"],
                    source_type="model_generated",
                    source_field="evidence_summary",
                    model_name=result["model_name"],
                    model_version=result["model_version"],
                    evidence=summary_evidence,
                )
            )
            for concept in result["concepts"]:
                records.append(
                    _upsert_content(
                        session,
                        video,
                        content_type="entity",
                        content_text=concept["text"],
                        source_type="model_generated",
                        source_field="evidence_concept",
                        model_name=result["model_name"],
                        model_version=result["model_version"],
                        evidence=[
                            {"content_record_id": evidence_id}
                            for evidence_id in concept["evidence_ids"]
                        ],
                    )
                )
            video.stage_statuses["summary"] = "completed"
        except Exception as exc:
            logger.exception("Summary generation failed for video %s", video.id)
            video.stage_statuses["summary"] = (
                f"failed: {type(exc).__name__}: {exc}"
            )

    def _embed(
        self,
        session: Session,
        video: Video,
        content_records: list[VideoContent],
    ) -> None:
        if not self.embedding_service.available:
            video.stage_statuses["embedding"] = (
                "unsupported: no embedding model configured"
            )
            return
        inputs = build_embedding_inputs(video, content_records)
        try:
            for item in inputs:
                vector = self.embedding_service.embed(item["text"])
                source_field = item["source_field"]
                content_record_id = item.get("content_record_id")
                source = (
                    f"content:{content_record_id}"
                    if content_record_id
                    else source_field
                )
                embedding = (
                    session.query(Embedding)
                    .filter_by(
                        video_id=video.id,
                        source=source,
                        model=self.embedding_service.model_name,
                        modality="text",
                    )
                    .one_or_none()
                )
                if embedding is None:
                    embedding = Embedding(
                        id=str(uuid.uuid4()),
                        video_id=video.id,
                        source=source,
                        model=self.embedding_service.model_name,
                        modality="text",
                    )
                    session.add(embedding)
                embedding.content_record_id = content_record_id
                embedding.model_version = self.embedding_service.model_version
                embedding.vector = self.embedding_service.serialize(vector)
            video.stage_statuses["embedding"] = "completed"
        except Exception as exc:
            logger.exception("Embedding generation failed for video %s", video.id)
            video.stage_statuses["embedding"] = (
                f"failed: {type(exc).__name__}: {exc}"
            )


def index_video(video_id: str) -> None:
    """FastAPI background-task entrypoint; persists each stage outcome."""
    session = SessionLocal()
    try:
        IndexingService().process(session, video_id)
    except Exception:
        session.rollback()
        video = session.query(Video).filter_by(id=video_id).one_or_none()
        if video is not None:
            video.status = "failed"
            statuses = dict(video.stage_statuses or {})
            statuses["indexing"] = "failed: unexpected indexing error"
            video.stage_statuses = statuses
            session.commit()
        logger.exception("Indexing failed unexpectedly for video %s", video_id)
    finally:
        session.close()


def index_video_batch(video_ids: list[str]) -> None:
    """Process one user's queued videos sequentially in a background task."""
    for video_id in video_ids:
        try:
            index_video(video_id)
        except Exception:
            logger.exception("Bulk indexing failed unexpectedly for video %s", video_id)
