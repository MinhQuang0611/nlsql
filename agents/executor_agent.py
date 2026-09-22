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
from db.connection import get_db_context, ch_execute, is_clickhouse, get_domain_engine_type
from graph.state import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_ROWS = 1000

_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def _execute_sql(sql: str, domain: str) -> tuple[list[dict[str, Any]], float]:
    """
    Thực thi SQL trên DB của domain, trả về (rows, elapsed_ms).
    Route sang ch_execute hoặc AsyncSession theo engine của CHÍNH domain đó.
    """
    start = time.perf_counter()

    if is_clickhouse(domain):
        # ch_execute trả về list[Row], cần convert sang list[dict]
        raw_rows = await ch_execute(domain, sql)
        # clickhouse-sqlalchemy rows có _fields hoặc _mapping
        if raw_rows and hasattr(raw_rows[0], "_mapping"):
            rows = [dict(row._mapping) for row in raw_rows[:MAX_ROWS]]
        elif raw_rows and hasattr(raw_rows[0], "_fields"):
            rows = [row._asdict() for row in raw_rows[:MAX_ROWS]]
        else:
            rows = [dict(enumerate(row)) for row in raw_rows[:MAX_ROWS]]
    else:
        async with get_db_context(domain) as db:
            result = await db.execute(text(sql))
            keys = list(result.keys())
            rows = [dict(zip(keys, row)) for row in result.fetchmany(MAX_ROWS)]

    elapsed_ms = (time.perf_counter() - start) * 1000
    return rows, elapsed_ms


async def executor_agent(state: AgentState) -> dict:
    domain = state.get("domain", "qldt")
    final_sql = state.get("final_sql", "").strip()

    if not final_sql:
        logger.error("[ExecutorAgent] final_sql is empty — cannot execute")
        return {
            "query_result": [],
            "row_count": 0,
            "execution_time_ms": 0.0,
            "executor_error": "No valid SQL to execute.",
        }

    # Chốt chặn SQL ghi. Trước đây điều kiện là `app_env != "development"`, nghĩa là
    # APP_ENV=development vô hiệu hoá hoàn toàn chốt này ngay trên DB production.
    # Nay phải bật tường minh ALLOW_WRITE_SQL=true mới bỏ chặn.
    if not settings.allow_write_sql and _DANGEROUS_PATTERN.search(final_sql):
        logger.error(
            "[ExecutorAgent] non-SELECT SQL BLOCKED (allow_write_sql=False, env=%s)",
            settings.app_env,
        )
        return {
            "query_result": [],
            "row_count": 0,
            "execution_time_ms": 0.0,
            "executor_error": (
                "Security Error: agent chỉ được phép chạy SELECT. "
                "Câu lệnh thay đổi dữ liệu đã bị chặn."
            ),
        }

    engine_type = get_domain_engine_type(domain)

    # 1. Ensure LIMIT is applied (làm TRƯỚC khi tính cache key để key khớp SQL thật sự chạy)
    clean_sql = final_sql.rstrip().rstrip(";")
    if "LIMIT" not in clean_sql.upper():
        if engine_type == "clickhouse":
            # ClickHouse dùng LIMIT trực tiếp, không cần subquery wrapper
            clean_sql = f"{clean_sql}\nLIMIT {MAX_ROWS}"
        else:
            clean_sql = f"SELECT * FROM (\n{clean_sql}\n) AS _subquery LIMIT {MAX_ROWS}"
    final_sql = clean_sql

    # 2. Redis Cache check
    #
    # Key phải gồm domain + engine + tên database, KHÔNG chỉ có câu hỏi người dùng.
    # Trước đây key = sha256(user_query), nên cùng một câu hỏi gửi vào /qldt/chat và
    # /tcns/chat dùng chung một ô cache và trả về kết quả của DB kia.
    # Ngoài ra key nay tính trên SQL thật sự chạy: cùng SQL => cùng kết quả, còn cùng
    # câu hỏi chưa chắc cùng SQL (schema đổi, few-shot đổi, retry ra SQL khác).
    db_name = settings.get_db_name(domain)
    sql_fingerprint = " ".join(final_sql.split()).lower()
    cache_key = "nlsql:q:{}".format(
        hashlib.sha256(
            f"{engine_type}|{domain}|{db_name}|{sql_fingerprint}".encode("utf-8")
        ).hexdigest()
    )
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info("[ExecutorAgent] REDIS CACHE HIT (domain=%s)", domain)
            cached_json = json.loads(cached_data)
            return {
                "query_result": cached_json["rows"],
                "row_count": cached_json["row_count"],
                "execution_time_ms": 0.0,
                "executor_error": None,
            }
    except Exception as e:
        logger.warning("[ExecutorAgent] Redis CACHE error: %s", e)

    logger.info(
        "[ExecutorAgent] executing on domain=%s engine=%s db=%s:\n%s",
        domain, engine_type, db_name, final_sql,
    )

    try:
        rows, elapsed_ms = await _execute_sql(final_sql, domain)
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
        if elapsed_ms > 2000 and engine_type != "clickhouse":
            logger.warning("[ExecutorAgent] SLOW QUERY DETECTED: %.1fms. Collecting physical plan...", elapsed_ms)
            try:
                async with get_db_context(domain) as slow_db:
                    explain_res = await slow_db.execute(text(f"EXPLAIN ANALYZE {final_sql}"))
                    explain_text = "\n".join(r[0] for r in explain_res.fetchall())
                    logger.warning("EXPLAIN ANALYZE OUTPUT:\n%s", explain_text)
            except Exception as e:
                logger.warning("[ExecutorAgent] Failed to collect EXPLAIN ANALYZE: %s", e)

        return {
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
            "query_result": [],
            "row_count": 0,
            "execution_time_ms": round(elapsed_ms, 2),
            "executor_error": error_msg,
        }