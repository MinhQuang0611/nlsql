"""
agents/knowledge_agent.py

Knowledge Agent: RAG từ Qdrant knowledge_collection.
Xử lý 2 loại intent:
  - knowledge_query: trả lời thuần từ tài liệu kiến thức, không cần DB
  - domain_query:   bổ sung ngữ cảnh kiến thức để DB pipeline xử lý chính xác hơn
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import QdrantClient

from config import get_settings
from graph.state import AgentState
from prompts.knowledge import KNOWLEDGE_ANSWER_SYSTEM, KNOWLEDGE_ANSWER_HUMAN

logger = logging.getLogger(__name__)
settings = get_settings()

_KNOWLEDGE_COLLECTION = "knowledge_collection"
_SEARCH_LIMIT = 5
_SCORE_THRESHOLD = 0.01   # knowledge docs thường ít chi tiết kỹ thuật hơn schema → threshold thấp hơn

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
    api_key=settings.openai_api_key,
)


@lru_cache(maxsize=1)
def _get_qdrant() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


@lru_cache(maxsize=1)
def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


def _search_knowledge(user_query: str) -> str:
    """Tìm kiếm tài liệu kiến thức liên quan trong Qdrant."""
    try:
        qdrant = _get_qdrant()
        embeddings = _get_embeddings()

        # Kiểm tra collection tồn tại
        collections = [c.name for c in qdrant.get_collections().collections]
        if _KNOWLEDGE_COLLECTION not in collections:
            logger.warning(
                "[KnowledgeAgent] Collection '%s' chưa tồn tại trong Qdrant. "
                "Hãy chạy script index_knowledge.py để tạo.",
                _KNOWLEDGE_COLLECTION,
            )
            return ""

        vector = embeddings.embed_query(user_query)
        response = qdrant.query_points(
            collection_name=_KNOWLEDGE_COLLECTION,
            query=vector,
            limit=_SEARCH_LIMIT,
            with_payload=True,
        )
        hits = response.points

        chunks: list[str] = []
        for hit in hits:
            if not hit.payload:
                continue
            score = hit.score if hasattr(hit, "score") else 0.0
            if score < _SCORE_THRESHOLD:
                continue
            content = hit.payload.get("content") or hit.payload.get("text") or ""
            source = hit.payload.get("source", "")
            if content:
                header = f"[Nguồn: {source}]" if source else ""
                chunks.append(f"{header}\n{content}".strip())

        if chunks:
            logger.info("[KnowledgeAgent] Tìm được %d chunks liên quan.", len(chunks))
            return "\n\n---\n\n".join(chunks)

        logger.info("[KnowledgeAgent] Không tìm thấy tài liệu đủ điểm (threshold=%.2f).", _SCORE_THRESHOLD)
        return ""

    except Exception as exc:
        logger.warning("[KnowledgeAgent] Qdrant search thất bại: %s", exc)
        return ""


async def knowledge_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: tìm kiếm tài liệu kiến thức từ Qdrant.

    - Với intent = knowledge_query: tìm ngữ cảnh + sinh câu trả lời ngay.
    - Với intent = domain_query:    chỉ tìm ngữ cảnh, để DB pipeline + domain_answer_agent tổng hợp.
    """
    user_query = state.get("user_query", "")
    intent = state.get("intent", "")
    history = state.get("history", [])

    logger.info("[KnowledgeAgent] query=%r intent=%s", user_query, intent)

    knowledge_context = _search_knowledge(user_query)

    # ── knowledge_query: dừng tại đây, trả lời ngay từ tài liệu ──────────
    if intent == "knowledge_query":
        if not knowledge_context:
            answer = (
                "Xin lỗi, tôi chưa tìm thấy thông tin liên quan trong tài liệu nghiệp vụ. "
                "Bạn vui lòng liên hệ bộ phận chức năng để được hỗ trợ thêm."
            )
            return {
                **state,
                "knowledge_context": "",
                "answer": answer,
                "answer_format": "text",
            }

        # Format history
        history_lines = []
        for msg in history:
            role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
            history_lines.append(f"{role}: {msg.get('content', '')}")

        messages = [
            SystemMessage(content=KNOWLEDGE_ANSWER_SYSTEM),
            HumanMessage(content=KNOWLEDGE_ANSWER_HUMAN.format(
                knowledge_context=knowledge_context,
                user_query=user_query,
            )),
        ]

        try:
            response = await _llm.ainvoke(messages)
            raw = response.content.strip()
            parsed = json.loads(raw)
            answer = parsed.get("answer", raw)
            answer_format = parsed.get("answer_format", "text")
        except Exception as exc:
            logger.error("[KnowledgeAgent] Parse lỗi: %s", exc)
            answer = knowledge_context  # fallback: trả nguyên context
            answer_format = "text"

        logger.info("[KnowledgeAgent] knowledge_query answered.")
        return {
            **state,
            "knowledge_context": knowledge_context,
            "answer": answer,
            "answer_format": answer_format,
        }

    # ── domain_query: chỉ lưu context, để DB pipeline chạy tiếp ─────────
    logger.info("[KnowledgeAgent] domain_query — lưu knowledge_context, tiếp tục DB pipeline.")
    return {
        **state,
        "knowledge_context": knowledge_context,
    }
