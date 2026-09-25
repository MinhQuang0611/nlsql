"""
Kiểm tra tĩnh câu SQL trước khi chạy: chốt chặn lệnh ghi + EXPLAIN dry-run.

Trước đây node này còn gọi LLM để "sửa" SQL khi EXPLAIN lỗi — một cơ chế sửa lỗi
thứ hai chồng lên vòng retry sql_gen đã có, với ba vấn đề: prompt ghi cứng
PostgreSQL trong khi domain chạy ClickHouse; SQL "đã sửa" được đưa thẳng sang
execute mà không EXPLAIN lại; và khi LLM tự khai chưa sửa được thì bản sửa bị
vứt đi để sql_gen sinh lại từ đầu. Nay node này KHÔNG gọi LLM: EXPLAIN lỗi thì
trả nguyên thông báo lỗi của DB về sql_gen — đó là gợi ý sửa tốt nhất.
"""
from __future__ import annotations

import logging
import re

from sqlalchemy import text

from db.connection import ch_execute, get_db_context, get_domain_engine_type
from graph.state import AgentState, SQLCorrectionResult

logger = logging.getLogger(__name__)

_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)


def _invalid(*issues: str) -> SQLCorrectionResult:
    return SQLCorrectionResult(is_valid=False, issues=list(issues), fixed_sql=None)


async def sql_check_agent(state: AgentState) -> dict:
    """
    Đọc : generated_sql, domain
    Ghi  : sql_correction, final_sql
    """
    generated_sql = (state.get("generated_sql") or "").strip()
    domain = state.get("domain", "qldt")
    engine_type = get_domain_engine_type(domain)

    if not generated_sql:
        return {"sql_correction": _invalid("Không sinh được câu SQL nào."), "final_sql": ""}

    match = _DANGEROUS_PATTERN.search(generated_sql)
    if match:
        issue = f"Câu SQL chứa lệnh không được phép: {match.group(0).upper()}. Chỉ được dùng SELECT."
        logger.warning("[SQLCheckAgent] BLOCKED: %s", issue)
        return {"sql_correction": _invalid(issue), "final_sql": ""}

    try:
        if engine_type == "clickhouse":
            await ch_execute(domain, f"EXPLAIN {generated_sql}")
        else:
            async with get_db_context(domain) as db:
                await db.execute(text(f"EXPLAIN {generated_sql}"))
    except Exception as db_exc:
        error_msg = str(db_exc).split("\n")[0][:500]
        logger.warning("[SQLCheckAgent] EXPLAIN FAIL (%s): %s", engine_type, error_msg)
        return {
            "sql_correction": _invalid(f"{engine_type} báo lỗi khi EXPLAIN: {error_msg}"),
            "final_sql": "",
        }

    logger.info("[SQLCheckAgent] EXPLAIN OK (%s).", engine_type)
    return {
        "sql_correction": SQLCorrectionResult(is_valid=True, issues=[], fixed_sql=generated_sql),
        "final_sql": generated_sql,
    }
