
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
from db.connection import get_db_context
from graph.state import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_ROWS = 1000  

_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)

redis_client = redis.from_url(settings.redis_url, decode_responses=True)

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
            "executor_error": f"Security Error: Modifying the database is only allowed on localhost (development env). Blocked query.",
        }

    # 1. Redis Cache check
    cache_key = None
    if user_query:
        query_hash = hashlib.sha256(user_query.encode('utf-8')).hexdigest()
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
            logger.warning(f"[ExecutorAgent] Redis CACHE error: {e}")

    # 2. Ensure LIMIT is applied using subquery wrapper if omitted
    clean_sql = final_sql.rstrip().rstrip(";")
    if "LIMIT" not in clean_sql.upper():
        clean_sql = f"SELECT * FROM (\n{clean_sql}\n) AS _subquery LIMIT {MAX_ROWS}"
    final_sql = clean_sql

    logger.info("[ExecutorAgent] executing SQL:\n%s", final_sql)
    start = time.perf_counter()

    try:
        async with get_db_context() as db:
            result = await db.execute(text(final_sql))
            keys = list(result.keys())
            rows: list[dict[str, Any]] = [
                dict(zip(keys, row)) for row in result.fetchmany(MAX_ROWS)
            ]

        elapsed_ms = (time.perf_counter() - start) * 1000
        row_count = len(rows)
        logger.info("[ExecutorAgent] OK — %d rows in %.1f ms", row_count, elapsed_ms)

        # 3. Cache the result
        if cache_key:
            try:
                cache_payload = {
                    "rows": rows,
                    "row_count": row_count
                }
                # 3600 seconds = 1 hour cache TTL
                await redis_client.setex(cache_key, 3600, json.dumps(cache_payload, default=str))
            except Exception as e:
                logger.warning(f"[ExecutorAgent] Redis SET error: {e}")

        # 4. Slow query EXPLAIN ANALYZE logging (if slow)
        if elapsed_ms > 2000:
            logger.warning(f"[ExecutorAgent] SLOW QUERY DETECTED: {elapsed_ms:.1f}ms. Collecting physical plan...")
            try:
                # We use a secondary connection so we don't interfere with main flow
                async with get_db_context() as slow_db:
                    explain_res = await slow_db.execute(text(f"EXPLAIN ANALYZE {final_sql}"))
                    explain_rows = explain_res.fetchall()
                    explain_text = "\n".join(r[0] for r in explain_rows)
                    logger.warning(f"EXPLAIN ANALYZE OUTPUT:\n{explain_text}")
            except Exception as e:
                logger.warning(f"[ExecutorAgent] Failed to collect EXPLAIN ANALYZE: {e}")

        return {
            **state,
            "query_result": rows,
            "row_count": row_count,
            "execution_time_ms": round(elapsed_ms, 2),
            "executor_error": None,
        }

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        error_msg = str(exc)
        logger.error("[ExecutorAgent] DB error: %s", error_msg)

        return {
            **state,
            "query_result": [],
            "row_count": 0,
            "execution_time_ms": round(elapsed_ms, 2),
            "executor_error": error_msg,
        }