from __future__ import annotations
import logging
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

from config import get_settings
from graph.state import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()

_FAQ_COLLECTION = "faq_collection"
_SEARCH_LIMIT = 4
_FAQ_THRESHOLD = 0.70

@lru_cache(maxsize=1)
def _get_qdrant() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

@lru_cache(maxsize=1)
def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

def _search_faq(user_query: str) -> tuple[dict|None, list[str]]:
    try:
        qdrant = _get_qdrant()
        embeddings = _get_embeddings()

        collections = [c.name for c in qdrant.get_collections().collections]
        if _FAQ_COLLECTION not in collections:
            return None, []

        vector = embeddings.embed_query(user_query)
        response = qdrant.query_points(
            collection_name=_FAQ_COLLECTION,
            query=vector,
            limit=_SEARCH_LIMIT,
            with_payload=True,
        )
        hits = response.points

        if not hits:
            return None, []

        best_hit = None
        recommend_questions = []

        for hit in hits:
            score = getattr(hit, "score", 0.0)
            payload = hit.payload or {}
            question = payload.get("cau_hoi", "")
            
            if score >= _FAQ_THRESHOLD and best_hit is None:
                best_hit = {
                    "answer": payload.get("cau_tra_loi", ""),
                    "score": score
                }
            elif question:
                recommend_questions.append(question)
                
            if len(recommend_questions) >= 3:
                break

        return best_hit, recommend_questions

    except Exception as exc:
        logger.warning(f"[FAQAgency] Lỗi tìm kiếm FAQ: {exc}")
        return None, []


async def faq_agent(state: AgentState) -> AgentState:
    user_query = state.get("user_query", "")
    logger.info(f"[FAQAgency] Đang tìm kiếm FAQ cho: {user_query}")

    best_hit, recommend_questions = _search_faq(user_query)

    if best_hit:
        logger.info(f"[FAQAgency] Trúng FAQ! Score: {best_hit['score']}")
        return {
            **state,
            "intent": "faq_answered",
            "answer": best_hit["answer"],
            "answer_format": "text",
            "recommend_questions": recommend_questions
        }

    logger.info("[FAQAgency] Không trúng FAQ, chuyển sang xử lý mặc định.")
    return state
