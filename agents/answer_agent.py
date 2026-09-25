"""
Node cuối: viết câu trả lời cho người dùng.

Trước đây LLM phải trả JSON {"answer", "answer_format"} và tầng API phải bóc dần
field `answer` khỏi JSON đang stream (utils/json_stream.py). answer_format thực ra
quyết định được bằng luật từ chart_config và row_count, nên nay LLM trả text thuần
và stream thẳng ra client.
"""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from prompts.answer import ANSWER_SYSTEM, ANSWER_HUMAN
from prompts.knowledge import DOMAIN_ANSWER_SYSTEM, DOMAIN_ANSWER_HUMAN
from utils.chat_history import format_history
from utils.llm import make_llm

logger = logging.getLogger(__name__)

_llm = make_llm()
_MAX_PREVIEW_ROWS = 10
_CHART_TYPES_WITH_AXES = {"bar", "line", "pie", "scatter"}


def _text(answer: str) -> dict:
    return {"answer": answer, "answer_format": "text"}


def decide_answer_format(chart_config: dict | None, row_count: int) -> str:
    if chart_config and chart_config.get("chart_type") in _CHART_TYPES_WITH_AXES:
        return "chart+text"
    if row_count > 1:
        return "table"
    return "text"


async def answer_agent(state: AgentState) -> dict:
    user_query = state["user_query"]
    intent = state.get("intent", "data_query")
    query_result = state.get("query_result", []) or []
    row_count = state.get("row_count", 0)
    chart_config = state.get("chart_config")
    executor_error = state.get("executor_error")

    if intent == "out_of_scope":
        return _text("Xin lỗi, câu hỏi này nằm ngoài phạm vi hệ thống. "
                     "Tôi chỉ có thể trả lời các câu hỏi liên quan đến dữ liệu trong database.")
    if intent == "greeting":
        return _text("Chào bạn! Tôi là trợ lý phân tích dữ liệu. "
                     "Bạn cần tôi truy xuất hay trực quan hóa dữ liệu gì hôm nay?")
    if intent == "schema_question":
        relevant = state.get("relevant_tables", [])
        return _text(f"Database có các bảng liên quan: {', '.join(relevant)}.")

    # sql_check từ chối tới lần cuối — không có SQL nào để chạy.
    if not state.get("final_sql"):
        issues = state.get("sql_correction", {}).get("issues", [])
        detail = f" ({issues[-1]})" if issues else ""
        return _text(f"Xin lỗi, tôi chưa tạo được truy vấn hợp lệ cho câu hỏi này{detail}. "
                     "Bạn có thể diễn đạt lại cụ thể hơn không?")
    if executor_error:
        return _text(f"Không thể thực thi truy vấn. Lỗi: {executor_error}")

    preview_rows = query_result[:_MAX_PREVIEW_ROWS]
    answer_format = decide_answer_format(chart_config, row_count)
    has_chart = answer_format == "chart+text"
    knowledge_context = state.get("knowledge_context", "")

    logger.info("[AnswerAgent] rows=%d format=%s has_knowledge=%s",
                row_count, answer_format, bool(knowledge_context))

    if knowledge_context and intent == "domain_query":
        messages = [
            SystemMessage(content=DOMAIN_ANSWER_SYSTEM),
            HumanMessage(content=DOMAIN_ANSWER_HUMAN.format(
                knowledge_context=knowledge_context, row_count=row_count,
                query_result=preview_rows, user_query=user_query,
            )),
        ]
    else:
        messages = [
            SystemMessage(content=ANSWER_SYSTEM),
            HumanMessage(content=ANSWER_HUMAN.format(
                user_query=user_query, row_count=row_count, query_result=preview_rows,
                has_chart="CÓ" if has_chart else "KHÔNG",
                history_text=format_history(state.get("history", [])),
            )),
        ]

    response = await _llm.ainvoke(messages)
    return {"answer": response.content.strip(), "answer_format": answer_format}
