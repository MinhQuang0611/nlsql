"""
Node đầu tiên sau FAQ: chọn domain + phân loại ý định trong MỘT lượt gọi LLM.

Trước đây là ba node nối tiếp — domain_router (LLM), intent (LLM), clarification
(copy chuỗi) — cùng đọc user_query + history, cùng structured output. Gộp lại
tiết kiệm một lượt LLM mỗi câu hỏi và bỏ được một node vô nghĩa.

Domain chỉ được hỏi LLM khi endpoint chưa chỉ định và registry có > 1 domain.
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from config import get_settings
from graph.state import AgentState
from prompts.router import (
    ROUTER_SYSTEM, ROUTER_HUMAN, ROUTER_DOMAIN_TASK, ROUTER_DOMAIN_SECTION,
)
from utils.chat_history import format_history
from utils.llm import make_llm

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = make_llm()

VALID_INTENTS = {
    "data_query", "chart_request", "schema_question", "knowledge_query",
    "domain_query", "greeting", "out_of_scope", "ambiguous",
}

_DEFAULT_CLARIFICATION = (
    "Câu hỏi của bạn còn khá chung chung. "
    "Bạn có thể mô tả cụ thể hơn bạn muốn xem dữ liệu gì không? "
    "(ví dụ: theo thời gian nào, đối tượng nào, hoặc chỉ tiêu cụ thể nào?)"
)


class RouteSchema(BaseModel):
    intent: str = Field(description=(
        'Một trong: "greeting", "data_query", "chart_request", "schema_question", '
        '"knowledge_query", "domain_query", "ambiguous", "out_of_scope".'
    ))
    domain: Optional[str] = Field(
        default=None,
        description="Mã cơ sở dữ liệu được chọn, viết y nguyên như danh sách. Bỏ trống nếu không được yêu cầu chọn.",
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description='Chỉ điền khi intent là "ambiguous": câu hỏi ngược lại để người dùng làm rõ.',
    )


def _resolve_preset_domain(state: AgentState, available: list[str]) -> tuple[str | None, str | None]:
    """Trả về (domain, lý do) nếu domain đã xác định không cần LLM, ngược lại (None, None)."""
    default_domain = available[0] if available else "qldt"
    preset = state.get("domain")
    if preset:
        if preset in available:
            return preset, "Được chỉ định bởi endpoint."
        logger.warning("[Router] domain '%s' không có trong registry %s — dùng '%s'",
                       preset, available, default_domain)
        return default_domain, f"Domain '{preset}' không tồn tại, rơi về mặc định."
    if len(available) <= 1:
        return default_domain, "Hệ thống chỉ có một cơ sở dữ liệu."
    return None, None


async def router_agent(state: AgentState) -> dict:
    """
    Đọc : user_query, history, domain (nếu endpoint đã gán)
    Ghi  : intent, domain, domain_reasoning, clarification_question, answer (khi ambiguous)
    """
    user_query = state.get("user_query", "")
    history = state.get("history", [])
    available = settings.list_domains()
    default_domain = available[0] if available else "qldt"

    domain, domain_reasoning = _resolve_preset_domain(state, available)
    ask_domain = domain is None

    domain_section = ""
    if ask_domain:
        domain_list = "\n".join(f"- {d}: {settings.get_domain_description(d)}" for d in available)
        domain_section = ROUTER_DOMAIN_SECTION.format(
            domain_list=domain_list, default_domain=default_domain,
        )

    messages = [
        SystemMessage(content=ROUTER_SYSTEM.format(
            domain_task=ROUTER_DOMAIN_TASK if ask_domain else "",
            domain_section=domain_section,
        )),
        HumanMessage(content=ROUTER_HUMAN.format(
            user_query=user_query,
            history_text=format_history(history),
        )),
    ]

    intent = "out_of_scope"
    clarification_question: str | None = None
    try:
        response = await _llm.with_structured_output(RouteSchema).ainvoke(messages)
        intent = response.intent if response.intent in VALID_INTENTS else "out_of_scope"
        if response.intent not in VALID_INTENTS:
            logger.warning("[Router] intent lạ %r — rơi về out_of_scope", response.intent)
        clarification_question = response.clarification_question

        if ask_domain:
            if response.domain in available:
                domain, domain_reasoning = response.domain, "LLM chọn theo mô tả nghiệp vụ."
            else:
                domain = default_domain
                domain_reasoning = f"LLM trả về domain không hợp lệ {response.domain!r}, rơi về mặc định."
                logger.warning("[Router] %s", domain_reasoning)
    except Exception as exc:
        logger.error("[Router] lỗi gọi LLM: %s", exc, exc_info=True)
        if ask_domain:
            domain, domain_reasoning = default_domain, "Mặc định (router lỗi)."

    logger.info("[Router] query=%r → intent=%s domain=%s (%s)",
                user_query, intent, domain, domain_reasoning)

    update: dict = {
        "intent": intent,
        "domain": domain,
        "domain_reasoning": domain_reasoning,
        "clarification_question": clarification_question,
    }
    # ambiguous kết thúc ngay tại đây — không cần node riêng chỉ để copy chuỗi.
    if intent == "ambiguous":
        update["answer"] = clarification_question or _DEFAULT_CLARIFICATION
        update["answer_format"] = "text"
    return update
