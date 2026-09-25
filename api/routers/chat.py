"""
Endpoint chat.

Một generator lõi `_run_chat()` chạy graph và phát ra các event; endpoint stream
bọc nó thành SSE, endpoint non-stream chỉ lấy event cuối. Trước đây hai đường này
là hai hàm ~200 dòng gần giống nhau, và mỗi domain lại có bộ endpoint riêng copy
nguyên body — nay tất cả gọi chung `_initial_state()` + `_run_chat()`.

Graph KHÔNG dùng checkpointer: history do client gửi lên mỗi request, và
checkpointer với thread_id = session_id từng làm state lượt trước rò sang lượt
sau (data_retry_count không reset → data_check không bao giờ retry từ câu thứ 2;
selected_tables của /chat_with_table dính sang /chat…).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import AsyncIterator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from api.schemas.chat import ChatRequest, ChatWithTableRequest, ChatResponse
from config import get_settings
from db.connection import get_internal_db_context
from db.models.chat_history import Conversation, Message
from graph.builder import get_graph_app
from utils.google_sheets import append_to_sheet
from utils.recommend import generate_recommend_questions

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])

# recursion_limit: đường đi xấu nhất (3 retry sql_check + 1 retry data_check)
# tốn ~20 super-step, sát mức mặc định 25 của LangGraph.
_RECURSION_LIMIT = 50

_MAX_STR = 300      # độ dài tối đa của một chuỗi trong state_update
_MAX_ITEMS = 5      # số phần tử tối đa của list/dict trong state_update
_MAX_DEPTH = 3      # state_update là kênh tiến trình/gỡ lỗi, không phải kênh dữ liệu

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    # Tắt buffering của nginx/reverse proxy — thiếu dòng này proxy gom cả
    # response rồi mới trả, client không thấy gì cho tới khi xong.
    "X-Accel-Buffering": "no",
}


# --------------------------------------------------------------------------
# Tiện ích
# --------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _json_safe(value, depth: int = 0):
    """Rút gọn một giá trị state thành JSON hợp lệ (cắt ở mức chuỗi / phần tử, không cắt giữa JSON)."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= _MAX_STR else value[:_MAX_STR] + f"… (+{len(value) - _MAX_STR} ký tự)"
    if depth >= _MAX_DEPTH:
        return f"<{type(value).__name__}>"
    if isinstance(value, dict):
        out = {str(k): _json_safe(v, depth + 1) for k, v in list(value.items())[:_MAX_ITEMS]}
        if len(value) > _MAX_ITEMS:
            out["…"] = f"+{len(value) - _MAX_ITEMS} khoá nữa"
        return out
    if isinstance(value, (list, tuple, set)):
        seq = list(value)
        out = [_json_safe(v, depth + 1) for v in seq[:_MAX_ITEMS]]
        if len(seq) > _MAX_ITEMS:
            out.append(f"… +{len(seq) - _MAX_ITEMS} mục nữa")
        return out
    return _json_safe(str(value), depth)


def _initial_state(request: ChatRequest, domain: Optional[str] = None) -> dict:
    """Mọi key theo-lượt được đặt tường minh để không phụ thuộc giá trị mặc định ngầm."""
    state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "history": [m.model_dump() for m in request.history],
        "retry_count": 0,
        "data_retry_count": 0,
    }
    if domain:
        state["domain"] = domain
    if isinstance(request, ChatWithTableRequest):
        state["selected_tables"] = request.selected_tables
    return state


async def _save_user_message(session_id: str, user_id: Optional[str], user_query: str) -> None:
    async with get_internal_db_context() as db:
        conv = (await db.execute(select(Conversation).where(Conversation.id == session_id))).scalar_one_or_none()
        if not conv:
            db.add(Conversation(
                id=session_id, user_id=user_id,
                title=user_query[:50] + ("..." if len(user_query) > 50 else ""),
            ))
        elif user_id and not conv.user_id:
            conv.user_id = user_id
        db.add(Message(conversation_id=session_id, role="user", content=user_query))
        await db.commit()


async def _save_assistant_message(session_id: str, response: ChatResponse, streaming: bool) -> None:
    async with get_internal_db_context() as db:
        db.add(Message(
            conversation_id=session_id, role="assistant", content=response.answer,
            intent=response.intent, sql_query=response.sql, error_message=response.error,
            execution_time_ms=response.execution_time_ms,
            metadata_json={
                "total_time": response.total_execution_time,
                "slowest_node": response.slowest_node,
                "streaming": streaming,
            },
        ))
        await db.commit()


# --------------------------------------------------------------------------
# Lõi: chạy graph, phát event
# --------------------------------------------------------------------------

async def _run_chat(
    initial_state: dict,
    user_id: Optional[str],
    num_recommend: int,
    streaming: bool,
) -> AsyncIterator[dict]:
    """
    Phát ra các event dạng dict:
      {"event": "connected"}
      {"event": "node_finish", "node", "execution_time_ms", "state_update"}
      {"event": "answer_token", "token"}
      {"event": "final_result", "data": ChatResponse}
    Ngoại lệ được ném ra ngoài để caller quyết định (SSE error event / HTTP 500).
    """
    yield {"event": "connected"}

    session_id = initial_state["session_id"]
    user_query = initial_state["user_query"]
    await _save_user_message(session_id, user_id, user_query)

    graph_app = get_graph_app()
    config = {"recursion_limit": _RECURSION_LIMIT}

    final_state = dict(initial_state)
    node_times: dict[str, float] = {}
    start_total = time.perf_counter()
    last_step = start_total
    streamed_answer = ""

    # "updates": node nào vừa xong (thanh tiến trình); "messages": token LLM sinh trong node.
    async for chunk in graph_app.astream(
        initial_state, config=config, stream_mode=["updates", "messages"], version="v2",
    ):
        chunk_type = chunk.get("type")

        if chunk_type == "messages":
            message, meta = chunk["data"]
            # Chỉ node answer sinh text cho người dùng; các node khác sinh JSON nội bộ.
            if meta.get("langgraph_node") != "answer":
                continue
            piece = getattr(message, "content", "") or ""
            if isinstance(piece, str) and piece:
                streamed_answer += piece
                yield {"event": "answer_token", "token": piece}
            continue

        if chunk_type != "updates":
            continue

        for node_name, state_update in chunk["data"].items():
            now = time.perf_counter()
            step_ms = round((now - last_step) * 1000, 2)
            last_step = now
            node_times[node_name] = step_ms
            logger.info("👉 STEP FINISHED: %s (%s ms)", node_name.upper(), step_ms)

            state_update = state_update or {}
            final_state.update(state_update)
            yield {
                "event": "node_finish",
                "node": node_name,
                "execution_time_ms": step_ms,
                "state_update": {k: _json_safe(v) for k, v in state_update.items()},
            }

    total_ms = round((time.perf_counter() - start_total) * 1000, 2)
    slowest_node = max(node_times, key=node_times.get) if node_times else None

    recommend_task = None
    if num_recommend > 0 and not final_state.get("recommend_questions"):
        recommend_task = asyncio.create_task(generate_recommend_questions(
            user_query=user_query, answer=final_state.get("answer", ""),
            history=final_state.get("history", []), num_recommend=num_recommend,
        ))

    response = ChatResponse(
        answer=final_state.get("answer", "Hệ thống gặp lỗi, không thể trả lời."),
        answer_format=final_state.get("answer_format", "text"),
        sql=final_state.get("final_sql") or None,
        data=final_state.get("query_result", []),
        chart_config=final_state.get("chart_config"),
        execution_time_ms=final_state.get("execution_time_ms", 0.0),
        total_execution_time=total_ms,
        node_execution_times=node_times,
        slowest_node=slowest_node,
        intent=final_state.get("intent", "unknown"),
        error=final_state.get("executor_error"),
        recommend_questions=final_state.get("recommend_questions") or [],
        clarification_question=final_state.get("clarification_question")
        if final_state.get("intent") == "ambiguous" else None,
    )
    if recommend_task:
        try:
            response.recommend_questions = await recommend_task
        except Exception as exc:
            logger.warning("[Chat] Không sinh được recommend questions: %s", exc)

    # Câu trả lời soạn sẵn (greeting, out_of_scope, lỗi SQL, clarification, FAQ,
    # knowledge_query) không đi qua LLM của node answer nên không có token —
    # gửi nguyên câu trong MỘT event, không giả lập gõ phím.
    if streaming and not streamed_answer and response.answer:
        yield {"event": "answer_token", "token": response.answer}

    yield {"event": "final_result", "data": response}

    await _save_assistant_message(session_id, response, streaming)
    settings = get_settings()
    if settings.google_sheet_url:
        asyncio.create_task(append_to_sheet(settings.google_sheet_url, [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session_id, user_query,
            str(response.answer), str(response.sql or ""), str(response.error or ""),
        ]))


async def _chat(request: ChatRequest, domain: Optional[str] = None) -> ChatResponse:
    logger.info("Chat query=%r (session=%s, domain=%s, history_len=%d)",
                request.query, request.session_id, domain, len(request.history))
    try:
        async for event in _run_chat(_initial_state(request, domain), request.user_id,
                                     request.num_recommend, streaming=False):
            if event["event"] == "final_result":
                return event["data"]
    except Exception as exc:
        logger.error("Error during graph execution: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    raise HTTPException(status_code=500, detail="Graph kết thúc mà không có kết quả.")


def _chat_stream(request: ChatRequest, domain: Optional[str] = None) -> StreamingResponse:
    async def gen():
        try:
            async for event in _run_chat(_initial_state(request, domain), request.user_id,
                                         request.num_recommend, streaming=True):
                if event["event"] == "final_result":
                    event = {"event": "final_result", "data": jsonable_encoder(event["data"])}
                yield _sse(event)
        except Exception as exc:
            logger.error("Error during streaming chat: %s", exc, exc_info=True)
            yield _sse({"event": "error", "detail": str(exc)})

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_SSE_HEADERS)


# --------------------------------------------------------------------------
# Endpoints — giữ nguyên URL để client hiện tại không phải đổi
# --------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    return await _chat(request)


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    return _chat_stream(request)


@router.post("/chat_with_table", response_model=ChatResponse)
async def chat_with_table_endpoint(request: ChatWithTableRequest) -> ChatResponse:
    return await _chat(request)


@router.post("/qldt/chat", response_model=ChatResponse, tags=["QLDT"])
async def qldt_chat_endpoint(request: ChatRequest) -> ChatResponse:
    return await _chat(request, "qldt")


@router.post("/qldt/chat/stream", tags=["QLDT"])
async def qldt_chat_stream_endpoint(request: ChatRequest):
    return _chat_stream(request, "qldt")


@router.post("/qldt/chat_with_table", response_model=ChatResponse, tags=["QLDT"])
async def qldt_chat_with_table_endpoint(request: ChatWithTableRequest) -> ChatResponse:
    return await _chat(request, "qldt")


@router.post("/tcns/chat", response_model=ChatResponse, tags=["TCNS"])
async def tcns_chat_endpoint(request: ChatRequest) -> ChatResponse:
    return await _chat(request, "tcns")


@router.post("/tcns/chat/stream", tags=["TCNS"])
async def tcns_chat_stream_endpoint(request: ChatRequest):
    return _chat_stream(request, "tcns")


@router.post("/tcns/chat_with_table", response_model=ChatResponse, tags=["TCNS"])
async def tcns_chat_with_table_endpoint(request: ChatWithTableRequest) -> ChatResponse:
    return await _chat(request, "tcns")
