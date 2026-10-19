from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.retrieval.hybrid_search import search_videos
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def run_search(
    payload: SearchRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SearchResponse:
    return search_videos(session, payload, user.id)
