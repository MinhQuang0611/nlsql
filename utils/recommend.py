"""
utils/recommend.py
Sinh danh sách câu hỏi gợi ý tiếp theo dựa trên lịch sử hội thoại và câu trả lời hiện tại.
"""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.7,
    api_key=settings.openai_api_key,
)

_SYSTEM_PROMPT = """\
Bạn là trợ lý phân tích dữ liệu thông minh. Nhiệm vụ của bạn là đề xuất các câu hỏi follow-up
mà người dùng nên hỏi tiếp theo dựa trên cuộc trò chuyện hiện tại.

Quy tắc:
- Câu hỏi phải liên quan đến chủ đề dữ liệu đang được thảo luận.
- Câu hỏi phải cụ thể, có thể trả lời bằng dữ liệu từ database.
- Không lặp lại các câu hỏi đã được hỏi trong lịch sử.
- Trả về đúng {num_recommend} câu hỏi.
- Trả về JSON array thuần túy, ví dụ: ["Câu hỏi 1", "Câu hỏi 2", "Câu hỏi 3"]
- KHÔNG thêm bất kỳ text ngoài JSON.
"""

_HUMAN_PROMPT = """\
Lịch sử hội thoại:
{history_text}

Câu hỏi vừa hỏi: {user_query}
Câu trả lời vừa nhận: {answer}

Hãy đề xuất {num_recommend} câu hỏi tiếp theo mà người dùng nên hỏi.

Lưu ý: Thông tin chỉ trong phạm vi hỏi đáp với cơ sở dữ liệu về quản lý đào tạo, sinh viên, ngành học, liên quan đến học viện, không liên quan đến các vấn đề khác và đây là . Không trả lời các câu hỏi không liên quan đến cơ sở dữ liệu.

"""


async def generate_recommend_questions(
    user_query: str,
    answer: str,
    history: list[dict],
    num_recommend: int = 3,
) -> list[str]:
    """
    Gọi LLM để sinh `num_recommend` câu hỏi gợi ý tiếp theo.

    Args:
        user_query: Câu hỏi vừa được đặt ra.
        answer: Câu trả lời từ agent.
        history: Danh sách dict {"role": "user"/"assistant", "content": "..."}.
        num_recommend: Số lượng câu hỏi gợi ý.

    Returns:
        Danh sách câu hỏi gợi ý (list[str]).
    """
    if num_recommend <= 0:
        return []

    # Format history
    history_lines: list[str] = []
    for msg in history:
        role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
        history_lines.append(f"{role}: {msg.get('content', '')}")
    history_text = "\n".join(history_lines) if history_lines else "(Không có lịch sử)"

    messages = [
        SystemMessage(
            content=_SYSTEM_PROMPT.format(num_recommend=num_recommend)
        ),
        HumanMessage(
            content=_HUMAN_PROMPT.format(
                history_text=history_text,
                user_query=user_query,
                answer=answer,
                num_recommend=num_recommend,
            )
        ),
    ]

    try:
        response = await _llm.ainvoke(messages)
        raw = response.content.strip()
        questions: list[str] = json.loads(raw)
        if not isinstance(questions, list):
            raise ValueError("LLM không trả về JSON array")
        return [str(q) for q in questions[:num_recommend]]
    except Exception as exc:
        logger.error("[Recommend] Lỗi sinh recommend questions: %s | raw=%r", exc, locals().get("raw", ""))
        return []
