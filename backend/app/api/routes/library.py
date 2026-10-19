from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.video import Video

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/stats")
def library_stats(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    videos = session.query(Video).filter_by(user_id=user.id).all()
    return {
        "saved_videos": len(videos),
        "indexed_videos": sum(video.status == "indexed" for video in videos),
        "pending_indexing": sum(
            video.status in {"queued", "pending", "processing"} for video in videos
        ),
        "status": "healthy",
    }
