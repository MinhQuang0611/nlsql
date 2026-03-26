"""
clarification_agent.py

Agent chuyên xử lý trường hợp câu hỏi của người dùng bị phân loại là "ambiguous".
Nó đọc `clarification_question` từ state (đã được sinh bởi intent_agent)
và đặt làm `answer` để trả về cho người dùng, yêu cầu họ cung cấp thêm ngữ cảnh.
"""

from __future__ import annotations

import logging

from graph.state import AgentState

logger = logging.getLogger(__name__)

_DEFAULT_CLARIFICATION = (
    "Câu hỏi của bạn còn khá chung chung. "
    "Bạn có thể mô tả cụ thể hơn bạn muốn xem dữ liệu gì không? "
    "(ví dụ: theo thời gian nào, đối tượng nào, hoặc chỉ tiêu cụ thể nào?)"
)


async def clarification_agent(state: AgentState) -> AgentState:
    clarification_question = state.get("clarification_question") or _DEFAULT_CLARIFICATION

    logger.info("[ClarificationAgent] returning clarification: %r", clarification_question)

    return {
        **state,
        "answer": clarification_question,
        "answer_format": "text",
    }
