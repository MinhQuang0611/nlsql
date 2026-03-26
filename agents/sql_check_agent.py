from __future__ import annotations

import json
import logging
import re
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text

from config import get_settings
from db.connection import engine
from graph.state import AgentState, SQLCorrectionResult, TableSchema
from prompts.sql_check import SQL_CORRECTION_SYSTEM, SQL_CORRECTION_HUMAN

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
    api_key=settings.openai_api_key,
)

_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)

class SQLCorrectionSchema(BaseModel):
    is_valid: bool = Field(description="Đánh dấu True nếu bạn tin rằng câu lệnh đã được sửa thành công.")
    issues: list[str] = Field(description="Mô tả các vấn đề bạn đã tìm thấy và cách bạn sửa chúng.")
    fixed_sql: str = Field(description="Câu lệnh SQL đã được sửa để chạy tốt trên cơ sở dữ liệu.")

def _hard_safety_check(sql: str) -> SQLCorrectionResult | None:
    match = _DANGEROUS_PATTERN.search(sql)
    if match:
        return SQLCorrectionResult(
            is_valid=False,
            issues=[f"Dangerous operation detected: {match.group(0).upper()}"],
            fixed_sql=None,
        )
    return None

def _format_schema_summary(schemas: list[TableSchema]) -> str:
    parts = []
    for s in schemas:
        col_names = ", ".join(c["name"] for c in s["columns"])
        parts.append(f"Table {s['table_name']}({col_names})")
    return "\n".join(parts)

async def sql_check_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: validate via EXPLAIN, if fail -> call LLM for correction.
    """
    generated_sql = state.get("generated_sql", "")
    schema_context = state.get("schema_context", [])
    schema_summary = _format_schema_summary(schema_context)

    logger.info("[SQLCheckAgent] validating SQL via EXPLAIN dry-run...")

    hard_result = _hard_safety_check(generated_sql)
    if hard_result:
        logger.warning("[SQLCheckAgent] BLOCKED by safety gate: %s", hard_result["issues"])
        return {**state, "sql_correction": hard_result, "final_sql": ""}

    # 1. Try to run EXPLAIN on PostgreSQL directly! If success, no need for LLM.
    try:
        async with engine.connect() as conn:
            await conn.execute(text(f"EXPLAIN {generated_sql}"))
            
        logger.info("[SQLCheckAgent] PASS (EXPLAIN OK). No LLM correction needed.")
        success_result = SQLCorrectionResult(
            is_valid=True,
            issues=[],
            fixed_sql=generated_sql
        )
        return {**state, "sql_correction": success_result, "final_sql": generated_sql}
        
    except Exception as db_exc:
        db_error_msg = str(db_exc)
        logger.warning("[SQLCheckAgent] FAIL at EXPLAIN: %s. Initiating LLM Correction...", db_error_msg)
        
        # 2. If fail, pass the error to LLM for Correction
        messages = [
            SystemMessage(content=SQL_CORRECTION_SYSTEM),
            HumanMessage(content=SQL_CORRECTION_HUMAN.format(
                user_query=state.get("user_query", ""),
                schema_context=schema_summary,
                invalid_sql=generated_sql,
                error_message=db_error_msg
            )),
        ]

        llm_structured = _llm.with_structured_output(SQLCorrectionSchema)
        correction_result = SQLCorrectionResult(
            is_valid=False,
            issues=[f"Postgres Error: {db_error_msg}"],
            fixed_sql=None
        )
        final_sql = ""

        try:
            response = await llm_structured.ainvoke(messages)
            correction_result = SQLCorrectionResult(
                is_valid=response.is_valid,
                issues=response.issues,
                fixed_sql=response.fixed_sql
            )
            final_sql = response.fixed_sql or ""
            logger.info("[SQLCheckAgent] LLM returned correction. issues=%s", response.issues)
            
            # Optionally we could EXPLAIN the fixed_sql again, but we will let builder loop handle it
            # if we wanted a multi-step loop. For now we will return it.
            if final_sql:
                # Let's do a quick safety check on the fixed SQL too
                hard_result2 = _hard_safety_check(final_sql)
                if hard_result2:
                    return {**state, "sql_correction": hard_result2, "final_sql": ""}
                
        except Exception as exc:
            logger.error("[SQLCheckAgent] LLM Correction failed: %s", exc)
            correction_result["issues"].append(f"LLM Validator error: {exc}")

        return {**state, "sql_correction": correction_result, "final_sql": final_sql}