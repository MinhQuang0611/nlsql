from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from graph.state import AgentState
from prompts.answer import ANSWER_SYSTEM, ANSWER_HUMAN
from prompts.knowledge import DOMAIN_ANSWER_SYSTEM, DOMAIN_ANSWER_HUMAN

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,  # Phải là 0 để đảm bảo kết quả deterministc, tránh số liệu bị diễn giải khác nhau
    api_key=settings.openai_api_key,
)

_MAX_PREVIEW_ROWS = 10  


async def answer_agent(state: AgentState) -> AgentState:

    user_query = state["user_query"]
    query_result = state.get("query_result", [])
    row_count = state.get("row_count", 0)
    chart_config = state.get("chart_config")
    knowledge_context = state.get("knowledge_context", "")
    intent = state.get("intent", "data_query")
    executor_error = state.get("executor_error")
    history = state.get("history", [])

    if intent == "out_of_scope":
        return {
            **state,
            "answer": (
                "Xin lỗi, câu hỏi này nằm ngoài phạm vi hệ thống. "
                "Tôi chỉ có thể trả lời các câu hỏi liên quan đến dữ liệu trong database."
            ),
            "answer_format": "text",
        }

    if intent == "greeting":
        return {
            **state,
            "answer": "Chào bạn! Tôi là trợ lý phân tích dữ liệu. Bạn cần tôi truy xuất hay trực quan hóa dữ liệu gì hôm nay?",
            "answer_format": "text",
        }

    if intent == "schema_question":
        relevant = state.get("relevant_tables", [])
        return {
            **state,
            "answer": f"Database có các bảng liên quan: {', '.join(relevant)}.",
            "answer_format": "text",
        }

    if executor_error:
        return {
            **state,
            "answer": f"Không thể thực thi truy vấn. Lỗi: {executor_error}",
            "answer_format": "text",
        }

    preview_rows = query_result[:_MAX_PREVIEW_ROWS]
    has_chart = chart_config is not None

    # Format history
    if history:
        lines = []
        for msg in history:
            role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
            lines.append(f"{role}: {msg.get('content', '')}")
        history_text = "\n".join(lines)
    else:
        history_text = "(Không có lịch sử hội thoại)"

    logger.info("[AnswerAgent] generating answer for %d rows, has_chart=%s, history_len=%d, has_knowledge=%s", row_count, has_chart, len(history), bool(knowledge_context))

    # domain_query: tổng hợp DB + kiến thức nghiệp vụ
    if knowledge_context and state.get("intent") == "domain_query":
        messages = [
            SystemMessage(content=DOMAIN_ANSWER_SYSTEM),
            HumanMessage(content=DOMAIN_ANSWER_HUMAN.format(
                knowledge_context=knowledge_context,
                row_count=row_count,
                query_result=preview_rows,
                user_query=user_query,
            )),
        ]
    else:
        messages = [
            SystemMessage(content=ANSWER_SYSTEM),
            HumanMessage(content=ANSWER_HUMAN.format(
                user_query=user_query,
                row_count=row_count,
                query_result=preview_rows,
                has_chart=has_chart,
                history_text=history_text,
            )),
        ]

    response = await _llm.ainvoke(messages)
    raw = response.content.strip()

    try:
        parsed = json.loads(raw)
        answer = parsed["answer"]
        answer_format = parsed.get("answer_format", "text")
        valid_formats = {"text", "table", "chart+text"}
        if answer_format not in valid_formats:
            answer_format = "chart+text" if has_chart else "table"
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("[AnswerAgent] parse error: %s", exc)
        answer = raw  
        answer_format = "chart+text" if has_chart else "text"

    logger.info("[AnswerAgent] answer_format=%s", answer_format)
    return {**state, "answer": answer, "answer_format": answer_format}