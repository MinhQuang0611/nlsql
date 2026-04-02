# from __future__ import annotations

# import logging
# from contextlib import asynccontextmanager
# from typing import AsyncGenerator

# # Monkeypatch cho asynch >= 0.2.2 tương thích với clickhouse-sqlalchemy
# import asynch
# if hasattr(asynch, "connection") and not hasattr(asynch, "connect"):
#     asynch.connect = asynch.connection

# from sqlalchemy import text
# from sqlalchemy.exc import OperationalError
# from sqlalchemy.ext.asyncio import (
#     AsyncEngine,
#     AsyncSession,
#     async_sessionmaker,
#     create_async_engine
# )

# from sqlalchemy.orm import DeclarativeBase

# from config import get_settings

# logger = logging.getLogger(__name__)
# settings = get_settings()

# def _build_engine() -> AsyncEngine:
#     return create_async_engine(
#         settings.database_url,
#         pool_size=settings.db_pool_size,
#         pool_timeout=settings.db_pool_timeout,
#         pool_pre_ping=True,
#         echo=settings.db_echo,
#         connect_args={"server_settings": {"statement_timeout": "30000"}}
#     )

# engine: AsyncEngine = _build_engine()

# AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
#     bind=engine,
#     expire_on_commit=False,
#     autoflush=False
# )

# class Base(DeclarativeBase):
#     pass

# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise

# @asynccontextmanager
# async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise

# async def check_db_connection() -> dict:
#     try:
#         async with engine.connect() as conn:
#             result = await conn.execute(text("SELECT version()"))
#             version = result.scalar()
#         logger.info(f"Kết nối tới Db thành công. Db version {version}")
#         return {"status": "ok", "version": version, "detail": "khong loi"}
#     except OperationalError as exc:
#         logger.error(f"Kết nối tới Db thất bại. Lỗi :{exc}")
#         return {"status": "ok", "version": "", "detail": str(exc)}
    
# async def init_db() -> None:
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     logger.info("Tạo Db thành công")

# async def close_db() -> None:
#     await engine.dispose()
#     logger.info("Db đã đóng")

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Base (dùng cho ORM models — chỉ hoạt động đầy đủ với Postgres)
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass

# ---------------------------------------------------------------------------
# Internal Backend Database (PostgreSQL) - Always used for Business Rules CRUD
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

internal_engine = create_async_engine(
    settings.internal_database_url,
    pool_size=settings.db_pool_size,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    echo=settings.db_echo,
)

InternalAsyncSessionLocal = async_sessionmaker(
    bind=internal_engine,
    expire_on_commit=False,
    autoflush=False,
)

@asynccontextmanager
async def get_internal_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with InternalAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_internal_db() -> None:
    """
    Khởi tạo database nội bộ:
    1. Tạo các bảng SQLAlchemy (Conversation, Message, ...)
    2. Chạy migrations cho LangGraph PostgresSaver (Checkpoint tables)
    """
    # 1. Khởi tạo SQLAlchemy models
    import db.models.chat_history  # noqa: F401
    async with internal_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Khởi tạo LangGraph checkpoint tables
    # Sử dụng from_conn_string để đảm bảo setup() chạy trong autocommit mode (cần cho CREATE INDEX CONCURRENTLY)
    from urllib.parse import quote_plus
    conn_str = (
        f"postgresql://{settings.postgres_user}:{quote_plus(settings.postgres_password)}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        f"?sslmode=disable"
    )
    async with AsyncPostgresSaver.from_conn_string(conn_str) as saver:
        await saver.setup()
        
    logger.info("Khởi tạo schema Internal Postgres và LangGraph checkpointer thành công")

# ---------------------------------------------------------------------------
# LangGraph Postgres Checkpointer
# ---------------------------------------------------------------------------
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

@asynccontextmanager
async def get_checkpoint_saver() -> AsyncGenerator[AsyncPostgresSaver, None]:
    """
    Tạo context manager cho AsyncPostgresSaver.
    Sử dụng internal database (Postgres).
    """
    # Xây dựng connection string cho psycopg (v3)
    from urllib.parse import quote_plus
    conn_str = (
        f"postgresql://{settings.postgres_user}:{quote_plus(settings.postgres_password)}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        f"?sslmode=disable"
    )
    
    async with AsyncConnectionPool(conn_str, max_size=settings.db_pool_size) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        # Bỏ qua await checkpointer.setup() ở đây vì đã chạy trong init_internal_db() lúc khởi động
        yield checkpointer

# ---------------------------------------------------------------------------
# Khởi tạo engine theo active_db
# ---------------------------------------------------------------------------

if settings.active_db == "clickhouse":
    # ── ClickHouse: dùng sync engine + HTTP driver ──────────────────────────
    from sqlalchemy import create_engine
    from sqlalchemy.engine import Engine as _SyncEngine

    from urllib.parse import quote_plus

    _ch_url = (
        f"clickhouse+http://{settings.ch_db_user}:{quote_plus(settings.ch_db_password)}"
        f"@{settings.ch_db_host}:{settings.ch_db_port}/{settings.ch_db_name}"
    )

    _sync_engine: _SyncEngine = create_engine(
        _ch_url,
        pool_pre_ping=True,
        echo=settings.db_echo,
    )

    # Không có AsyncSession cho ClickHouse — dùng helper bên dưới
    engine = None
    AsyncSessionLocal = None

    def _ch_run(query: str, params: dict | None = None):
        with _sync_engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            try:
                return result.fetchall()
            except Exception:
                return []

    async def _ch_execute(query: str, params: dict | None = None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _ch_run, query, params)

else:
    # ── Postgres: async engine + AsyncSession ────────────────────────────────
    from urllib.parse import quote_plus
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    _pg_url = (
        f"postgresql+asyncpg://{settings.pg_db_user}:{quote_plus(settings.pg_db_password)}"
        f"@{settings.pg_db_host}:{settings.pg_db_port}/{settings.pg_db_name}"
        f"?ssl=disable"
    )

    engine: AsyncEngine = create_async_engine(
        _pg_url,
        pool_size=settings.db_pool_size,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        echo=settings.db_echo,
        connect_args={"server_settings": {"statement_timeout": "30000"}},
    )

    AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )


# ---------------------------------------------------------------------------
# get_db / get_db_context  (chỉ dùng được khi active_db = postgres)
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if settings.active_db == "clickhouse":
        raise NotImplementedError("get_db() không hỗ trợ ClickHouse — dùng ch_execute()")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    if settings.active_db == "clickhouse":
        raise NotImplementedError("get_db_context() không hỗ trợ ClickHouse — dùng ch_execute()")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Public helper cho ClickHouse query (dùng ở business logic)
# ---------------------------------------------------------------------------

async def ch_execute(query: str, params: dict | None = None) -> list:
    """
    Chạy raw SQL trên ClickHouse bất đồng bộ.
    Chỉ dùng khi active_db = 'clickhouse'.
    """
    if settings.active_db != "clickhouse":
        raise NotImplementedError("ch_execute() chỉ dùng khi active_db = 'clickhouse'")
    return await _ch_execute(query, params)


# ---------------------------------------------------------------------------
# check_db_connection  (được gọi trong main.py lifespan + /health)
# ---------------------------------------------------------------------------

async def check_db_connection() -> dict:
    try:
        if settings.active_db == "clickhouse":
            rows = await _ch_execute("SELECT version()")
            version = rows[0][0] if rows else "unknown"
        else:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()

        logger.info("Kết nối %s thành công. Version: %s", settings.active_db, version)
        return {"status": "ok", "version": version, "detail": ""}

    except Exception as exc:
        logger.error("Kết nối %s thất bại: %s", settings.active_db, exc)
        return {"status": "error", "version": "", "detail": str(exc)}


# ---------------------------------------------------------------------------
# init_db  (được gọi trong main.py khi app_env = development)
# ---------------------------------------------------------------------------

async def init_db() -> None:
    if settings.active_db == "clickhouse":
        # ClickHouse không dùng SQLAlchemy ORM metadata
        # Tạo bảng thủ công nếu cần, hoặc bỏ qua
        logger.info("ClickHouse: bỏ qua init_db() — tạo bảng thủ công nếu cần")
        return

    async with engine.begin() as conn:
        # Prevent ClickHouse Base from being created on external Postgres
        pass
    logger.info("Khởi tạo schema External Postgres thành công")



# ---------------------------------------------------------------------------
# close_db  (được gọi trong main.py khi shutdown)
# ---------------------------------------------------------------------------

async def close_db() -> None:
    await internal_engine.dispose()
    logger.info("Đã đóng kết nối Internal Postgres")

    if settings.active_db == "clickhouse":
        _sync_engine.dispose()
        logger.info("Đã đóng kết nối ClickHouse")
    else:
        await engine.dispose()
        logger.info("Đã đóng kết nối Postgres")