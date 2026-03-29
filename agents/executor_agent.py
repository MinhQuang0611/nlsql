from __future__ import annotations

import logging
import time
from typing import Any
import json
import hashlib
import redis.asyncio as redis
import re
from sqlalchemy import text

from config import get_settings
from db.connection import get_db_context, ch_execute
from graph.state import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_ROWS = 1000

_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def _execute_sql(sql: str) -> tuple[list[dict[str, Any]], float]:
    """
    Thực thi SQL trên DB đang active, trả về (rows, elapsed_ms).
    Tự động route sang ch_execute hoặc AsyncSession theo active_db.
    """
    start = time.perf_counter()

    if settings.active_db == "clickhouse":
        # ch_execute trả về list[Row], cần convert sang list[dict]
        raw_rows = await ch_execute(sql)
        # clickhouse-sqlalchemy rows có _fields hoặc _mapping
        if raw_rows and hasattr(raw_rows[0], "_mapping"):
            rows = [dict(row._mapping) for row in raw_rows[:MAX_ROWS]]
        elif raw_rows and hasattr(raw_rows[0], "_fields"):
            rows = [row._asdict() for row in raw_rows[:MAX_ROWS]]
        else:
            rows = [dict(enumerate(row)) for row in raw_rows[:MAX_ROWS]]
    else:
        async with get_db_context() as db:
            result = await db.execute(text(sql))
            keys = list(result.keys())
            rows = [dict(zip(keys, row)) for row in result.fetchmany(MAX_ROWS)]

    elapsed_ms = (time.perf_counter() - start) * 1000
    return rows, elapsed_ms


async def executor_agent(state: AgentState) -> AgentState:

    final_sql = state.get("final_sql", "").strip()
    user_query = state.get("user_query", "").strip()

    if not final_sql:
        logger.error("[ExecutorAgent] final_sql is empty — cannot execute")
        return {
            **state,
            "query_result": [],
            "row_count": 0,
            "execution_time_ms": 0.0,
            "executor_error": "No valid SQL to execute.",
        }

    if settings.app_env != "development" and _DANGEROUS_PATTERN.search(final_sql):
        logger.error("[ExecutorAgent] non-Select SQL execution BLOCKED in environment: %s", settings.app_env)
        return {
            **state,
            "query_result": [],
            "row_count": 0,
            "execution_time_ms": 0.0,
            "executor_error": "Security Error: Modifying the database is only allowed on localhost (development env). Blocked query.",
        }

    # 1. Redis Cache check
    cache_key = None
    if user_query:
        query_hash = hashlib.sha256(user_query.encode("utf-8")).hexdigest()
        cache_key = f"nlsql:query:{query_hash}"
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info("[ExecutorAgent] REDIS CACHE HIT for query")
                cached_json = json.loads(cached_data)
                return {
                    **state,
                    "query_result": cached_json["rows"],
                    "row_count": cached_json["row_count"],
                    "execution_time_ms": 0.0,
                    "executor_error": None,
                }
        except Exception as e:
            logger.warning("[ExecutorAgent] Redis CACHE error: %s", e)

    # 2. Ensure LIMIT is applied
    clean_sql = final_sql.rstrip().rstrip(";")
    if "LIMIT" not in clean_sql.upper():
        if settings.active_db == "clickhouse":
            # ClickHouse dùng LIMIT trực tiếp, không cần subquery wrapper
            clean_sql = f"{clean_sql}\nLIMIT {MAX_ROWS}"
        else:
            clean_sql = f"SELECT * FROM (\n{clean_sql}\n) AS _subquery LIMIT {MAX_ROWS}"
    final_sql = clean_sql

    logger.info("[ExecutorAgent] executing SQL on %s:\n%s", settings.active_db, final_sql)

    try:
        rows, elapsed_ms = await _execute_sql(final_sql)
        row_count = len(rows)
        logger.info("[ExecutorAgent] OK — %d rows in %.1f ms", row_count, elapsed_ms)

        # 3. Cache the result
        if cache_key:
            try:
                cache_payload = {"rows": rows, "row_count": row_count}
                await redis_client.setex(cache_key, 3600, json.dumps(cache_payload, default=str))
            except Exception as e:
                logger.warning("[ExecutorAgent] Redis SET error: %s", e)

        # 4. Slow query logging (Postgres only — EXPLAIN ANALYZE không có trên ClickHouse)
        if elapsed_ms > 2000 and settings.active_db != "clickhouse":
            logger.warning("[ExecutorAgent] SLOW QUERY DETECTED: %.1fms. Collecting physical plan...", elapsed_ms)
            try:
                async with get_db_context() as slow_db:
                    explain_res = await slow_db.execute(text(f"EXPLAIN ANALYZE {final_sql}"))
                    explain_text = "\n".join(r[0] for r in explain_res.fetchall())
                    logger.warning("EXPLAIN ANALYZE OUTPUT:\n%s", explain_text)
            except Exception as e:
                logger.warning("[ExecutorAgent] Failed to collect EXPLAIN ANALYZE: %s", e)

        return {
            **state,
            "query_result": rows,
            "row_count": row_count,
            "execution_time_ms": round(elapsed_ms, 2),
            "executor_error": None,
        }

    except Exception as exc:
        elapsed_ms = 0.0
        error_msg = str(exc)
        logger.error("[ExecutorAgent] DB error: %s", error_msg)
        return {
            **state,
            "query_result": [],
            "row_count": 0,
            "execution_time_ms": round(elapsed_ms, 2),
            "executor_error": error_msg,
        }