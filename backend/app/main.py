import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.videos import router as videos_router
from app.api.routes.search import router as search_router
from app.api.routes.library import router as library_router
from app.services.embedding_service import EmbeddingService, EmbeddingUnavailable

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    embedding_service = EmbeddingService()
    if embedding_service.available:
        started = time.perf_counter()
        try:
            await asyncio.to_thread(
                embedding_service.embed,
                "ReelRecall embedding model warm-up",
            )
        except EmbeddingUnavailable as exc:
            logger.warning("Embedding model warm-up failed: %s", exc)
        else:
            logger.info(
                "Embedding model warmed in %.1f seconds",
                time.perf_counter() - started,
            )
    yield


app = FastAPI(title="ReelRecall API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(videos_router)
app.include_router(search_router)
app.include_router(library_router)

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "ReelRecall API is running"}
