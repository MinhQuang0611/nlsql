import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from agents.answer_agent import answer_agent
from agents.chart_agent import chart_agent
from agents.data_check_agent import data_check_agent
from agents.executor_agent import executor_agent
from agents.faq_agent import faq_agent
from agents.knowledge_agent import knowledge_agent
from agents.router_agent import router_agent
from agents.schema_agent import schema_agent
from agents.sql_check_agent import sql_check_agent
from agents.sql_gen_agent import sql_gen_agent
from graph.state import AgentState

logger = logging.getLogger(__name__)

MAX_SQL_RETRY = 3


def route_after_faq(state: AgentState) -> str:
    return END if state.get("intent") == "faq_answered" else "router"


def route_after_router(state: AgentState) -> str | list[str]:
    intent = state.get("intent")
    if intent in ("data_query", "chart_request", "domain_query"):
        return ["schema", "knowledge"]
    if intent == "schema_question":
        return "schema"
    if intent == "knowledge_query":
        return "knowledge"
    if intent == "ambiguous":
        return END           # router đã đặt câu hỏi làm rõ vào `answer`
    return "answer"          # greeting, out_of_scope — câu trả lời soạn sẵn


def route_after_retrieval(state: AgentState) -> str:
    return "answer" if state.get("intent") == "schema_question" else "sql_gen"


def route_after_sql_check(state: AgentState) -> str:
    if state.get("sql_correction", {}).get("is_valid"):
        return "execute"
    if state.get("retry_count", 0) >= MAX_SQL_RETRY:
        logger.warning("[Builder] SQL không hợp lệ sau %d lần — bỏ cuộc.", MAX_SQL_RETRY)
        return "answer"      # answer_agent nhìn final_sql rỗng để báo lỗi
    return "sql_gen"


def route_after_data_check(state: AgentState) -> str:
    """data_check tự chấp nhận kết quả khi hết lượt, nên không có nguy cơ lặp vô hạn."""
    return "chart" if state.get("data_check_is_valid", True) else "sql_gen"


def build_graph() -> Any:
    """
    Không dùng checkpointer. Lịch sử hội thoại do client gửi lên trong mỗi request,
    và graph không có interrupt — checkpointer chỉ khiến state của lượt trước
    (data_retry_count, selected_tables, query_result…) rò sang lượt sau.
    """
    def inc_retry(state: AgentState) -> dict:
        return {"retry_count": state.get("retry_count", 0) + 1}

    def inc_data_retry(state: AgentState) -> dict:
        return {"data_retry_count": state.get("data_retry_count", 0) + 1}

    builder = StateGraph(AgentState)

    builder.add_node("faq", faq_agent)
    builder.add_node("router", router_agent)
    builder.add_node("schema", schema_agent)
    builder.add_node("knowledge", knowledge_agent)
    builder.add_node("retrieval_join", lambda state: {})   # chỉ là điểm hợp nhất hai nhánh
    builder.add_node("sql_gen", sql_gen_agent)
    builder.add_node("sql_check", sql_check_agent)
    builder.add_node("inc_retry", inc_retry)
    builder.add_node("execute", executor_agent)
    builder.add_node("data_check", data_check_agent)
    builder.add_node("inc_data_retry", inc_data_retry)
    builder.add_node("chart", chart_agent)
    builder.add_node("answer", answer_agent)

    builder.add_edge(START, "faq")
    builder.add_conditional_edges("faq", route_after_faq, {"router": "router", END: END})

    builder.add_conditional_edges(
        "router", route_after_router,
        {"schema": "schema", "knowledge": "knowledge", "answer": "answer", END: END},
    )

    # knowledge_query: knowledge_agent đã sinh câu trả lời — kết thúc, không đi qua
    # answer_agent (trước đây answer_agent ghi đè bằng "không tìm thấy dữ liệu").
    builder.add_conditional_edges(
        "knowledge",
        lambda s: END if s.get("intent") == "knowledge_query" else "retrieval_join",
        {END: END, "retrieval_join": "retrieval_join"},
    )
    builder.add_edge("schema", "retrieval_join")
    builder.add_conditional_edges(
        "retrieval_join", route_after_retrieval, {"answer": "answer", "sql_gen": "sql_gen"},
    )

    # Vòng 1: sql_gen → sql_check (EXPLAIN) → (execute | sửa lại)
    builder.add_edge("sql_gen", "sql_check")
    builder.add_conditional_edges(
        "sql_check", route_after_sql_check,
        {"execute": "execute", "sql_gen": "inc_retry", "answer": "answer"},
    )
    builder.add_edge("inc_retry", "sql_gen")

    # Vòng 2: execute → data_check → (chart | sửa lại)
    builder.add_edge("execute", "data_check")
    builder.add_conditional_edges(
        "data_check", route_after_data_check, {"chart": "chart", "sql_gen": "inc_data_retry"},
    )
    builder.add_edge("inc_data_retry", "sql_gen")

    builder.add_edge("chart", "answer")
    builder.add_edge("answer", END)

    return builder.compile()


_cached_app = None


def get_graph_app() -> Any:
    """Singleton graph đã compile."""
    global _cached_app
    if _cached_app is None:
        _cached_app = build_graph()
    return _cached_app
