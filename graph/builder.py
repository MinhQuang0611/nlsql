import logging
from typing import Any
from langgraph.graph import StateGraph, START, END

from graph.state import AgentState
from agents.intent_agent import intent_agent
from agents.schema_agent import schema_agent
from agents.knowledge_agent import knowledge_agent
from agents.sql_plan_agent import sql_plan_agent
from agents.sql_gen_agent import sql_gen_agent
from agents.sql_check_agent import sql_check_agent
from agents.executor_agent import executor_agent
from agents.chart_agent import chart_agent
from agents.answer_agent import answer_agent
from agents.clarification_agent import clarification_agent
from agents.faq_agent import faq_agent

logger = logging.getLogger(__name__)

def route_after_faq(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "faq_answered":
        return "answer"  # Hoặc trực tiếp END tuỳ thiết kế, ở đây chuyển về answer để answer_agent pass thẳng hoặc in ra format tuỳ ý. Chờ duyệt log answer_agent
        # Nhưng theo logic answer_agent, nếu intent lạ nó sẽ sinh answer lỗi. Ghi đè.
        # Ở đây FAQAgent đã gán state['answer']. Ta có thể End luôn
        return END
    return "intent"

def route_after_intent(state: AgentState) -> str | list[str]:
    intent = state.get("intent")
    if intent == "domain_query":
        return ["schema", "knowledge"]
    if intent == "data_query" or intent == "chart_request":
        return ["schema", "knowledge"]
    if intent == "schema_question":
        return "schema"
    if intent == "knowledge_query":
        return "knowledge"
    if intent == "ambiguous":
        return "clarification"
    return "answer"  # greeting, out_of_scope

def route_after_retrieval(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "knowledge_query" or intent == "schema_question":
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


def build_graph(checkpointer: Any = None) -> Any:
    def inc_retry(state: AgentState) -> dict:
        return {"retry_count": state.get("retry_count", 0) + 1}

    builder = StateGraph(AgentState)

    builder.add_node("faq", faq_agent)
    builder.add_node("intent", intent_agent)
    builder.add_node("knowledge", knowledge_agent)
    builder.add_node("schema", schema_agent)
    builder.add_node("sql_plan", sql_plan_agent)
    builder.add_node("sql_gen", sql_gen_agent)
    builder.add_node("sql_check", sql_check_agent)
    builder.add_node("inc_retry", inc_retry)
    builder.add_node("execute", executor_agent)
    builder.add_node("chart", chart_agent)
    builder.add_node("answer", answer_agent)
    builder.add_node("clarification", clarification_agent)

    builder.add_edge(START, "faq")

    builder.add_conditional_edges(
        "faq",
        route_after_faq,
        {
            "intent": "intent",
            END: END,
        }
    )

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

    # Join point for parallel retrieval
    builder.add_node("retrieval_join", lambda state: state)
    builder.add_edge("schema", "retrieval_join")
    builder.add_edge("knowledge", "retrieval_join")

    builder.add_conditional_edges(
        "retrieval_join",
        route_after_retrieval,
        {
            "answer": "answer",
            "sql_plan": "sql_plan",
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

    app = builder.compile(checkpointer=checkpointer)
    return app


_cached_app = None

def get_graph_app(checkpointer: Any = None) -> Any:
    """
    Returns a singleton instance of the compiled graph.
    """
    global _cached_app
    if _cached_app is None:
        _cached_app = build_graph(checkpointer=checkpointer)
    return _cached_app

