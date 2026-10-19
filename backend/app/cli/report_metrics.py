import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.embedding import Embedding
from app.models.video import Video
from app.models.video_content import VideoContent
from app.services.embedding_service import is_searchable_content


def _percentage(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(100 * numerator / denominator, 2)


def _stage_outcome(status: str) -> str:
    normalized = status.strip().casefold()
    for outcome in (
        "completed",
        "empty",
        "failed",
        "unsupported",
        "skipped",
        "queued",
        "pending",
    ):
        if normalized == outcome or normalized.startswith(f"{outcome}:"):
            return outcome
    return "other"


def collect_metrics() -> dict[str, Any]:
    session = SessionLocal()
    try:
        videos = session.query(Video).all()
        content_records = session.query(VideoContent).all()
        embeddings = session.query(Embedding).all()

        searchable_records = [
            record for record in content_records if is_searchable_content(record)
        ]
        evidence_video_ids = {record.video_id for record in searchable_records}
        searchable_record_ids = {record.id for record in searchable_records}
        linked_vectors = [
            embedding
            for embedding in embeddings
            if embedding.content_record_id in searchable_record_ids
            and embedding.model == settings.embedding_model
        ]
        linked_record_ids = {embedding.content_record_id for embedding in linked_vectors}
        videos_with_content_vectors = {
            record.video_id
            for record in searchable_records
            if record.id in linked_record_ids
        }

        stage_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
        for video in videos:
            for stage, stage_status in (video.stage_statuses or {}).items():
                stage_outcomes[stage][_stage_outcome(str(stage_status))] += 1

        model_counts = Counter(embedding.model for embedding in embeddings)
        saved_count = len(videos)
        content_video_count = len(evidence_video_ids)
        vector_video_count = len(videos_with_content_vectors)
        return {
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "library": {
                "saved_videos": saved_count,
                "video_status_counts": dict(Counter(video.status for video in videos)),
            },
            "indexing": {
                "videos_with_completed_extracted_content": content_video_count,
                "extracted_content_coverage_percent": _percentage(
                    content_video_count, saved_count
                ),
                "completed_searchable_content_records": len(searchable_records),
                "content_record_counts": dict(
                    Counter(
                        f"{record.content_type}:{record.processing_status}"
                        for record in content_records
                    )
                ),
                "stage_outcomes": {
                    stage: dict(counts)
                    for stage, counts in sorted(stage_outcomes.items())
                },
            },
            "embeddings": {
                "configured_model": settings.embedding_model or None,
                "all_vectors": len(embeddings),
                "vectors_linked_to_current_searchable_content": len(linked_vectors),
                "videos_with_content_vectors": vector_video_count,
                "content_vector_coverage_percent": _percentage(
                    vector_video_count, content_video_count
                ),
                "model_counts": dict(model_counts),
                "semantic_search_ready": bool(
                    settings.embedding_model.strip() and linked_vectors
                ),
            },
        }
    finally:
        session.close()


def main() -> None:
    print(json.dumps(collect_metrics(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
