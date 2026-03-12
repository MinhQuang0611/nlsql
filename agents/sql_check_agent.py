
from __future__ import annotations

import json
import logging
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text

from config import get_settings
from db.connection import engine
from graph.state import AgentState, SQLCheckResult, TableSchema
from prompts.sql_check import SQL_CHECK_SYSTEM, SQL_CHECK_HUMAN

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


def _hard_safety_check(sql: str) -> SQLCheckResult | None:
    """
    Fast regex safety gate — runs before LLM to catch obvious threats.
    Returns a blocking SQLCheckResult if dangerous, else None.
    """
    match = _DANGEROUS_PATTERN.search(sql)
    if match:
        return SQLCheckResult(
            is_valid=False,
            issues=[f"Dangerous operation detected: {match.group(0).upper()}"],
            fixed_sql=None,
        )
    return None


def _format_schema_summary(schemas: list[TableSchema]) -> str:
    return ", ".join(
        f"{s['table_name']}({', '.join(c['name'] for c in s['columns'])})"
        for s in schemas
    )


async def sql_check_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: validate and optionally fix generated SQL.

    Reads  : state["generated_sql"], state["schema_context"]
    Writes : state["sql_check"], state["final_sql"]
    """
    generated_sql = state.get("generated_sql", "")
    schema_context = state.get("schema_context", [])
    schema_summary = _format_schema_summary(schema_context)

    logger.info("[SQLCheckAgent] validating SQL…")

    hard_result = _hard_safety_check(generated_sql)
    if hard_result:
        logger.warning("[SQLCheckAgent] BLOCKED by safety gate: %s", hard_result["issues"])
        return {**state, "sql_check": hard_result, "final_sql": ""}

    messages = [
        SystemMessage(content=SQL_CHECK_SYSTEM),
        HumanMessage(content=SQL_CHECK_HUMAN.format(
            generated_sql=generated_sql,
            schema_context=schema_summary,
        )),
    ]

    response = await _llm.ainvoke(messages)
    raw = response.content.strip()

    try:
        parsed = json.loads(raw)
        check_result = SQLCheckResult(
            is_valid=bool(parsed.get("is_valid", False)),
            issues=parsed.get("issues", []),
            fixed_sql=parsed.get("fixed_sql"),
        )
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("[SQLCheckAgent] parse error: %s", exc)
        check_result = SQLCheckResult(
            is_valid=False,
            issues=[f"Validator parse error: {exc}"],
            fixed_sql=None,
        )

    if check_result["is_valid"]:
        final_sql = check_result["fixed_sql"] or generated_sql
        # Try EXPLAIN to verify correctness at ClickHouse level
        try:
            async with engine.connect() as conn:
                await conn.execute(text(f"EXPLAIN {final_sql}"))
            logger.info("[SQLCheckAgent] PASS%s (EXPLAIN OK)",
                        " (auto-fixed)" if check_result["fixed_sql"] else "")
        except Exception as db_exc:
            logger.warning("[SQLCheckAgent] FAIL at EXPLAIN: %s", db_exc)
            check_result["is_valid"] = False
            check_result["issues"].append(f"ClickHouse syntax or schema error: {db_exc}")
            final_sql = ""
    else:
        final_sql = ""
        logger.warning("[SQLCheckAgent] FAIL — issues: %s", check_result["issues"])

    return {**state, "sql_check": check_result, "final_sql": final_sql}