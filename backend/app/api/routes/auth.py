import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenRead, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["authentication"])


def _token_response(user: User, token: str | None = None) -> TokenRead:
    return TokenRead(
        access_token=token or create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
        user=user,
    )


@router.post("/register", response_model=TokenRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, session: Session = Depends(get_db)) -> TokenRead:
    if session.query(User).filter_by(email=payload.email).one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
    )
    token = create_access_token(user.id)
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc
    session.refresh(user)
    return _token_response(user, token)


@router.post("/login", response_model=TokenRead)
def login(payload: UserLogin, session: Session = Depends(get_db)) -> TokenRead:
    user = session.query(User).filter_by(email=payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user)


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user
