from __future__ import annotations

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
    """Tạo các bảng SQLAlchemy nội bộ (Conversation, Message, ...)."""
    import db.models.chat_history  # noqa: F401
    async with internal_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Khởi tạo schema Internal Postgres thành công")


# ---------------------------------------------------------------------------
# Khởi tạo engine theo domain registry
#
# Trước đây file này rẽ nhánh MỘT LẦN theo settings.active_db, nên toàn bộ domain
# buộc phải nằm trên cùng loại engine. Nay mỗi domain tự khai engine của nó
# (settings.get_domain_engine), cho phép qldt ở ClickHouse còn tcns ở PostgreSQL.
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

domains = settings.list_domains()
engines: dict[str, "AsyncEngine"] = {}        # domain postgres -> async engine
AsyncSessionLocals: dict[str, async_sessionmaker] = {}
_sync_engines: dict[str, object] = {}          # domain clickhouse -> sync engine


def get_domain_engine_type(domain: str) -> str:
    """'postgres' | 'clickhouse' cho một domain. Domain lạ rơi về engine mặc định."""
    if domain not in domains:
        return settings.active_db.strip().lower()
    return settings.get_domain_engine(domain)


def is_clickhouse(domain: str) -> bool:
    return get_domain_engine_type(domain) == "clickhouse"


for _domain in domains:
    _engine_type = settings.get_domain_engine(_domain)

    if _engine_type == "clickhouse":
        # ClickHouse: sync engine + HTTP driver (asynch driver không ổn định)
        _sync_engines[_domain] = create_engine(
            settings.get_database_url_sync(_domain),
            pool_pre_ping=True,
            echo=settings.db_echo,
        )
    else:
        _pg_engine: AsyncEngine = create_async_engine(
            settings.get_database_url(_domain),
            pool_size=settings.db_pool_size,
            pool_timeout=settings.db_pool_timeout,
            pool_pre_ping=True,
            echo=settings.db_echo,
            connect_args={"server_settings": {"statement_timeout": "30000"}},
        )
        engines[_domain] = _pg_engine
        AsyncSessionLocals[_domain] = async_sessionmaker(
            bind=_pg_engine,
            expire_on_commit=False,
            autoflush=False,
        )

logger.info(
    "Domain registry: %s",
    {d: settings.get_domain_engine(d) for d in domains},
)


def _ch_run(domain: str, query: str, params: dict | None = None):
    if domain not in _sync_engines:
        return []
    with _sync_engines[domain].connect() as conn:
        result = conn.execute(text(query), params or {})
        try:
            return result.fetchall()
        except Exception:
            return []


async def _ch_execute(domain: str, query: str, params: dict | None = None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _ch_run, domain, query, params)


# ---------------------------------------------------------------------------
# get_db / get_db_context  (chỉ dùng được khi active_db = postgres)
# ---------------------------------------------------------------------------

async def get_db(domain: str = "qldt") -> AsyncGenerator[AsyncSession, None]:
    if is_clickhouse(domain):
        raise NotImplementedError(
            f"get_db() không hỗ trợ ClickHouse (domain={domain}) — dùng ch_execute()"
        )
    if domain not in AsyncSessionLocals:
        raise KeyError(f"Domain '{domain}' không có engine PostgreSQL trong registry")
    async with AsyncSessionLocals[domain]() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context(domain: str = "qldt") -> AsyncGenerator[AsyncSession, None]:
    if is_clickhouse(domain):
        raise NotImplementedError(
            f"get_db_context() không hỗ trợ ClickHouse (domain={domain}) — dùng ch_execute()"
        )
    if domain not in AsyncSessionLocals:
        raise KeyError(f"Domain '{domain}' không có engine PostgreSQL trong registry")
    async with AsyncSessionLocals[domain]() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Public helper cho ClickHouse query (dùng ở business logic)
# ---------------------------------------------------------------------------

async def ch_execute(domain: str, query: str, params: dict | None = None) -> list:
    """
    Chạy raw SQL trên ClickHouse bất đồng bộ.
    Chỉ dùng cho domain có engine = 'clickhouse'.
    """
    if not is_clickhouse(domain):
        raise NotImplementedError(
            f"ch_execute() chỉ dùng cho domain ClickHouse — '{domain}' đang là "
            f"'{get_domain_engine_type(domain)}'"
        )
    return await _ch_execute(domain, query, params)


# ---------------------------------------------------------------------------
# check_db_connection  (được gọi trong main.py lifespan + /health)
# ---------------------------------------------------------------------------

async def check_db_connection() -> dict:
    """
    Kiểm tra từng domain độc lập. Một domain hỏng không làm cả hệ thống báo lỗi —
    trước đây vòng lặp nằm trong một try chung nên domain đầu tiên fail là dừng hết.
    """
    versions: dict[str, str] = {}
    failures: dict[str, str] = {}

    for domain in domains:
        try:
            if is_clickhouse(domain):
                rows = await _ch_execute(domain, "SELECT version()")
                versions[domain] = str(rows[0][0]) if rows else "unknown"
                table_rows = await _ch_execute(domain, "SHOW TABLES")
            else:
                async with engines[domain].connect() as conn:
                    result = await conn.execute(text("SELECT version()"))
                    versions[domain] = str(result.scalar())
                    table_rows = (await conn.execute(text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    ))).fetchall()

            # Database tồn tại nhưng rỗng vẫn kết nối được — và router sẽ vẫn
            # route câu hỏi vào đó rồi fail ở bước lấy schema. Cảnh báo sớm để dễ chẩn đoán.
            if not table_rows:
                logger.warning(
                    "Domain '%s' kết nối được nhưng KHÔNG CÓ BẢNG NÀO (db=%s). "
                    "Mọi câu hỏi route vào domain này sẽ thất bại. "
                    "Cân nhắc bỏ nó khỏi DOMAINS_ENABLED cho tới khi có dữ liệu.",
                    domain, settings.get_db_name(domain),
                )
        except Exception as exc:
            failures[domain] = str(exc)
            logger.error("Kết nối domain '%s' thất bại: %s", domain, exc)

    if versions:
        logger.info("Kết nối DB OK cho domain: %s", list(versions))
    if failures:
        return {
            "status": "degraded" if versions else "error",
            "version": str(versions),
            "detail": str(failures),
        }
    return {"status": "ok", "version": str(versions), "detail": ""}


# ---------------------------------------------------------------------------
# init_db  (được gọi trong main.py khi app_env = development)
# ---------------------------------------------------------------------------

async def init_db() -> None:
    if not engines:
        logger.info("Không có domain PostgreSQL — bỏ qua init_db()")
        return

    for domain, eng in engines.items():
        async with eng.begin() as conn:
            pass
    logger.info("Khởi tạo schema External Postgres thành công cho: %s", list(engines))


# ---------------------------------------------------------------------------
# close_db  (được gọi trong main.py khi shutdown)
# ---------------------------------------------------------------------------

async def close_db() -> None:
    await internal_engine.dispose()
    logger.info("Đã đóng kết nối Internal Postgres")

    for domain, eng in _sync_engines.items():
        eng.dispose()
    if _sync_engines:
        logger.info("Đã đóng kết nối ClickHouse: %s", list(_sync_engines))

    for domain, eng in engines.items():
        await eng.dispose()
    if engines:
        logger.info("Đã đóng kết nối Postgres: %s", list(engines))