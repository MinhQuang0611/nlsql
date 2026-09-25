from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from config import get_settings
from db.connection import get_domain_engine_type
from graph.state import AgentState
from prompts.dialect import get_dialect_label, get_dialect_rules
from prompts.sql_gen import SQL_GEN_SYSTEM, SQL_GEN_HUMAN, SQL_GEN_RETRY_HINT
from utils.chat_history import format_history
from utils.llm import make_llm
from utils.schema_format import format_schema_context, format_business_context

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = make_llm(model=settings.sql_gen_model)


class SQLGenerationSchema(BaseModel):
    # `plan` đứng TRƯỚC `sql`: với structured output, thứ tự field chính là thứ tự
    # model sinh token, nên kế hoạch được viết ra trước và SQL bám theo nó.
    # Đây là phần việc của sql_plan_agent cũ, gộp vào đây để bớt một lượt LLM.
    plan: str = Field(description="Kế hoạch suy luận theo 6 bước: bảng, cột, lọc, JOIN, tổng hợp, sắp xếp.")
    sql: str = Field(description="Câu lệnh SQL thuần tuý, đúng dialect, chỉ SELECT.")


def _fetch_few_shot(domain: str, user_query: str) -> str:
    """Lấy tối đa 3 ví dụ (câu hỏi → SQL) gần nghĩa nhất từ collection theo domain."""
    if not settings.qdrant_url:
        return "Không có ví dụ."
    collection = f"few_shot_collection_{domain}"
    try:
        qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        embeddings = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
        response = qdrant.query_points(
            collection_name=collection,
            query=embeddings.embed_query(user_query),
            limit=3,
        )
        lines = [
            f"Q: {hit.payload['question']}\nSQL: {hit.payload['sql']}"
            for hit in response.points if hit.payload
        ]
        logger.info("[SQLGenAgent] %d few-shot từ '%s'.", len(lines), collection)
        return "\n\n".join(lines) if lines else "Không có ví dụ."
    except Exception as exc:
        logger.warning("[SQLGenAgent] few-shot từ '%s' thất bại: %s", collection, exc)
        return "Không có ví dụ."


async def sql_gen_agent(state: AgentState) -> dict:
    """
    Đọc : user_query, schema_context, business_context, history, retry hints
    Ghi  : generated_sql, sql_reasoning, sql_correction (reset), final_sql (reset)
    """
    user_query = state.get("user_query", "")
    domain = state.get("domain", "qldt")
    engine_type = get_domain_engine_type(domain)
    retry_count = state.get("retry_count", 0)
    data_retry_count = state.get("data_retry_count", 0)

    # Gợi ý sửa lỗi gộp từ hai nguồn: sql_check (EXPLAIN lỗi) và data_check (kết quả bất thường).
    issues: list[str] = []
    if retry_count > 0:
        issues.extend(state.get("sql_correction", {}).get("issues", []))
    if data_retry_count > 0:
        issues.extend(state.get("data_check_issues", []))
    retry_hint = SQL_GEN_RETRY_HINT.format(issues="\n".join(f"  - {i}" for i in issues)) if issues else ""

    logger.info("[SQLGenAgent] attempt=%d (data_retry=%d) query=%r",
                retry_count + 1, data_retry_count, user_query)

    messages = [
        SystemMessage(content=SQL_GEN_SYSTEM.format(
            dialect_name=get_dialect_label(engine_type),
            dialect_rules=get_dialect_rules(engine_type),
        )),
        HumanMessage(content=SQL_GEN_HUMAN.format(
            user_query=user_query,
            schema_context=format_schema_context(state.get("schema_context", [])),
            business_context=format_business_context(state.get("business_context", [])),
            few_shot_examples=_fetch_few_shot(domain, user_query),
            retry_hint=retry_hint,
            history_text=format_history(state.get("history", [])),
        )),
    ]

    generated_sql, plan = "", ""
    try:
        response = await _llm.with_structured_output(SQLGenerationSchema).ainvoke(messages)
        generated_sql = response.sql.strip()
        plan = response.plan
    except Exception as exc:
        logger.error("[SQLGenAgent] sinh SQL thất bại: %s", exc, exc_info=True)

    logger.info("[SQLGenAgent] plan=\n%s\nsql=\n%s", plan, generated_sql)
    return {
        "generated_sql": generated_sql,
        "sql_reasoning": plan,
        "sql_correction": {"is_valid": False, "issues": [], "fixed_sql": None},
        "final_sql": "",
    }
