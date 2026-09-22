
from __future__ import annotations

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from db.connection import check_db_connection, close_db, init_db, init_internal_db
from api.routers.chat import router as chat_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from scripts.index_schema import main as index_schema_main



settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


SCHEMA_INDEX_RETRIES = 5
SCHEMA_INDEX_RETRY_DELAY = 3.0


async def _index_schema_with_retry() -> None:
    """Index schema vào Qdrant, retry vì Qdrant có thể chưa nhận HTTP ngay khi container start."""
    last_error: Exception = RuntimeError("schema indexing did not run")
    for attempt in range(1, SCHEMA_INDEX_RETRIES + 1):
        try:
            await index_schema_main()
            return
        except Exception as e:
            last_error = e
            if attempt < SCHEMA_INDEX_RETRIES:
                logger.warning(
                    "Schema indexing lỗi (lần %d/%d): %s — thử lại sau %.0fs",
                    attempt, SCHEMA_INDEX_RETRIES, e, SCHEMA_INDEX_RETRY_DELAY,
                )
                await asyncio.sleep(SCHEMA_INDEX_RETRY_DELAY)
    raise last_error


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting nlsql [env=%s]", settings.app_env)

    db_status = await check_db_connection()
    if db_status["status"] == "error":
        logger.critical("DB not reachable on startup: %s", db_status["detail"])
        raise RuntimeError(f"Cannot connect to database: {db_status['detail']}")
    if db_status["status"] == "degraded":
        # Một domain hỏng không nên làm sập cả hệ thống — các domain còn lại vẫn phục vụ được.
        logger.error(
            "DB degraded — có domain không kết nối được: %s. Các domain OK: %s",
            db_status["detail"], db_status["version"],
        )

    logger.info("DB OK — %s", db_status["version"])

    if settings.app_env == "development":
        await init_db()
        await init_internal_db()

    logger.info("Checking/indexing schema...")
    try:
        await _index_schema_with_retry()
    except Exception as se:
        logger.error("Schema indexing bỏ qua (non-fatal): %s", se)

    # Tự động sync knowledge từ Google Sheet (không block nếu lỗi)
    try:
        from scripts.index_knowledge import run as sync_knowledge
        logger.info("Syncing knowledge from Google Sheet...")
        synced = await asyncio.to_thread(sync_knowledge, False)  # force=False → upsert
        logger.info("Knowledge sync done: %d entries.", synced)
    except Exception as ke:
        logger.warning("Knowledge sync skipped (non-fatal): %s", ke)

    logger.info("nlsql ready ")
    yield

    logger.info("Shutting down nlsql…")
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="nlsql",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # app.mount(
    #     "/frontend",
    #     StaticFiles(directory="app/frontend", html=True),
    #     name="frontend"
    # )
    
    origins = (
        ["*"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from api.routers.tables import router as tables_router
    from api.routers.chart import router as chart_router
    from api.routers.knowledge import router as knowledge_router
    from api.routers.faq import router as faq_router
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(tables_router, prefix="/api/v1")
    app.include_router(chart_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    app.include_router(faq_router, prefix="/api/v1")

    # Static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/chat", include_in_schema=False)
    async def chat_page():
        return FileResponse(os.path.join(static_dir, "chat.html"))

    @app.get("/manage_knowledge", include_in_schema=False)
    async def manage_knowledge_page():
        return FileResponse(os.path.join(static_dir, "manage_knowledge.html"))

    @app.get("/manage_faq", include_in_schema=False)
    async def manage_faq_page():
        return FileResponse(os.path.join(static_dir, "manage_faq.html"))




    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root() -> dict:
        return {"service": "nlsql", "version": "0.1.0", "status": "ok"}

    @app.get("/health", tags=["Health"])
    async def health() -> JSONResponse:
        db = await check_db_connection()
        healthy = db["status"] == "ok"
        payload = {
            "status": "healthy" if healthy else "degraded",
            "db": db,
            "env": settings.app_env,
        }
        return JSONResponse(
            content=payload,
            status_code=200 if healthy else 503,
        )

    return app




app = create_app()