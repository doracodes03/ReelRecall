import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.embedding import Embedding
from app.models.user import User
from app.models.video import Video
from app.models.video_content import VideoContent
from app.schemas.video import BulkReindexRead, ExtractedContentRead, VideoCreate, VideoRead
from app.services.indexing_service import index_video, index_video_batch
from app.utils.url_validation import normalize_video_url

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=list[VideoRead])
def list_videos(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Video]:
    return (
        session.query(Video)
        .filter_by(user_id=user.id)
        .order_by(Video.saved_at.desc())
        .all()
    )


@router.post("", response_model=VideoRead, status_code=status.HTTP_202_ACCEPTED)
def save_video(
    payload: VideoCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Video:
    try:
        canonical_url, platform, external_id = normalize_video_url(str(payload.url))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = (
        session.query(Video)
        .filter_by(user_id=user.id, canonical_url=canonical_url)
        .first()
    )
    if existing is not None:
        if (
            payload.permission_status != "unknown"
            and existing.permission_status != payload.permission_status
        ):
            existing.permission_status = payload.permission_status
            existing.status = "queued"
            existing.stage_statuses = {
                **(existing.stage_statuses or {}),
                "indexing": "queued",
            }
            session.commit()
            session.refresh(existing)
            background_tasks.add_task(index_video, existing.id)
        return existing

    video = Video(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title="",
        url=canonical_url,
        canonical_url=canonical_url,
        source=platform,
        external_video_id=external_id,
        source_metadata={},
        metadata_status="pending",
        permission_status=payload.permission_status,
        manual_category=payload.manual_category,
        manual_category_source="user" if payload.manual_category else None,
        curation_notes=payload.curation_notes,
        curation_notes_source="user" if payload.curation_notes else None,
        stage_statuses={"metadata": "queued"},
        status="queued",
        saved_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(video)
    session.commit()
    session.refresh(video)
    background_tasks.add_task(index_video, video.id)
    return video


@router.post(
    "/reindex-all",
    response_model=BulkReindexRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def reindex_all_videos(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BulkReindexRead:
    videos = (
        session.query(Video)
        .filter_by(user_id=user.id)
        .with_for_update()
        .all()
    )
    queued_ids: list[str] = []
    already_active = 0
    now = datetime.now(timezone.utc)
    for video in videos:
        if video.status in {"queued", "processing"}:
            already_active += 1
            continue
        video.status = "queued"
        video.stage_statuses = {
            **(video.stage_statuses or {}),
            "indexing": "queued",
        }
        video.updated_at = now
        queued_ids.append(video.id)

    session.commit()
    if queued_ids:
        background_tasks.add_task(index_video_batch, queued_ids)
    return BulkReindexRead(
        total_count=len(videos),
        queued_count=len(queued_ids),
        already_active_count=already_active,
        queued_video_ids=queued_ids,
    )


@router.get("/{video_id}", response_model=VideoRead)
def get_video(
    video_id: str,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Video:
    video = (
        session.query(Video)
        .filter_by(id=video_id, user_id=user.id)
        .one_or_none()
    )
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/content", response_model=list[ExtractedContentRead])
def get_video_content(
    video_id: str,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VideoContent]:
    video = (
        session.query(Video)
        .filter_by(id=video_id, user_id=user.id)
        .one_or_none()
    )
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return (
        session.query(VideoContent)
        .filter_by(video_id=video.id)
        .order_by(VideoContent.timestamp_start)
        .all()
    )


@router.post("/{video_id}/reindex", response_model=VideoRead, status_code=status.HTTP_202_ACCEPTED)
def reindex_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Video:
    video = (
        session.query(Video)
        .filter_by(id=video_id, user_id=user.id)
        .one_or_none()
    )
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    video.status = "queued"
    video.stage_statuses = {
        **(video.stage_statuses or {}),
        "indexing": "queued",
    }
    video.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(video)
    background_tasks.add_task(index_video, video.id)
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: str,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    video = (
        session.query(Video)
        .filter_by(id=video_id, user_id=user.id)
        .one_or_none()
    )
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    session.query(Embedding).filter_by(video_id=video.id).delete()
    session.query(VideoContent).filter_by(video_id=video.id).delete()
    session.delete(video)
    session.commit()
