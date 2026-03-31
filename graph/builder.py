import logging
from typing import Any
from langgraph.graph import StateGraph, START, END

from graph.state import AgentState
from agents.intent_agent import intent_agent
from agents.schema_agent import schema_agent
from agents.sql_plan_agent import sql_plan_agent
from agents.sql_gen_agent import sql_gen_agent
from agents.sql_check_agent import sql_check_agent
from agents.executor_agent import executor_agent
from agents.chart_agent import chart_agent
from agents.answer_agent import answer_agent
from agents.clarification_agent import clarification_agent
from agents.knowledge_agent import knowledge_agent

logger = logging.getLogger(__name__)


def route_after_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if intent in ("data_query", "chart_request", "schema_question"):
        return "schema"
    if intent in ("domain_query", "knowledge_query"):
        return "knowledge"
    if intent == "ambiguous":
        return "clarification"
    return "answer"  # greeting, out_of_scope


def route_after_knowledge(state: AgentState) -> str:
    """
    - knowledge_query: Knowledge Agent đã sinh answer → kết thúc ngay
    - domain_query:    chỉ lưu context → tiếp tục DB pipeline (schema → sql_plan ...)
    """
    intent = state.get("intent")
    if intent == "knowledge_query":
        return "answer"
    return "schema"   # domain_query


def route_after_schema(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "schema_question":
        return "answer"
    return "sql_plan"


def route_after_sql_check(state: AgentState) -> str:
    correction = state.get("sql_correction", {})
    if correction.get("is_valid"):
        return "execute"

    retry_count = state.get("retry_count", 0)
    if retry_count >= 3:
        logger.warning("[Builder] SQL validation/correction failed 3 times. Giving up.")
        return "execute"

    return "sql_gen"


def build_graph() -> Any:

    def inc_retry(state: AgentState) -> dict:
        return {"retry_count": state.get("retry_count", 0) + 1}

    builder = StateGraph(AgentState)

    # ── Nodes ───────────────────────────────────────────────────────────────
    builder.add_node("intent", intent_agent)
    builder.add_node("knowledge", knowledge_agent)   # Knowledge / Domain RAG
    builder.add_node("schema", schema_agent)

    builder.add_node("sql_plan", sql_plan_agent)
    builder.add_node("sql_gen", sql_gen_agent)
    builder.add_node("sql_check", sql_check_agent)
    builder.add_node("inc_retry", inc_retry)

    builder.add_node("execute", executor_agent)
    builder.add_node("chart", chart_agent)
    builder.add_node("answer", answer_agent)
    builder.add_node("clarification", clarification_agent)

    # ── Edges ────────────────────────────────────────────────────────────────
    builder.add_edge(START, "intent")

    # intent → {schema | knowledge | answer | clarification}
    builder.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "schema": "schema",
            "knowledge": "knowledge",
            "answer": "answer",
            "clarification": "clarification",
        }
    )

    # knowledge → {answer (knowledge_query) | schema (domain_query)}
    builder.add_conditional_edges(
        "knowledge",
        route_after_knowledge,
        {
            "answer": "answer",
            "schema": "schema",
        }
    )

    # schema → {sql_plan | answer (schema_question)}
    builder.add_conditional_edges(
        "schema",
        route_after_schema,
        {
            "sql_plan": "sql_plan",
            "answer": "answer",
        }
    )

    builder.add_edge("sql_plan", "sql_gen")
    builder.add_edge("sql_gen", "sql_check")

    builder.add_conditional_edges(
        "sql_check",
        route_after_sql_check,
        {
            "execute": "execute",
            "sql_gen": "inc_retry",
        }
    )
    builder.add_edge("inc_retry", "sql_gen")

    builder.add_edge("execute", "chart")
    builder.add_edge("chart", "answer")
    builder.add_edge("answer", END)
    builder.add_edge("clarification", END)

    app = builder.compile()
    return app
