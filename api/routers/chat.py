import logging
import time
from fastapi import APIRouter, HTTPException, Depends
from api.schemas.chat import ChatRequest, ChatWithTableRequest, ChatResponse
from graph.builder import build_graph
from utils.recommend import generate_recommend_questions
from utils.google_sheets import append_to_sheet
from config import get_settings
from datetime import datetime

from db.connection import get_checkpoint_saver, get_internal_db_context
from db.models.chat_history import Conversation, Message
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])



async def _process_chat(initial_state: dict) -> ChatResponse:
    num_recommend: int = initial_state.pop("num_recommend", 3)
    session_id = initial_state.get("session_id", "default")
    user_id = initial_state.get("user_id")
    user_query = initial_state.get("user_query", "")

    # 1. Khởi tạo/Cập nhật Conversation trong DB
    async with get_internal_db_context() as db:
        # Check if conversation exists
        stmt = select(Conversation).where(Conversation.id == session_id)
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        
        if not conv:
            conv = Conversation(
                id=session_id, 
                user_id=user_id,
                title=user_query[:50] + ("..." if len(user_query) > 50 else "")
            )
            db.add(conv)
        elif user_id and not conv.user_id:
            conv.user_id = user_id
        
        # Lưu tin nhắn của người dùng
        user_msg = Message(
            conversation_id=session_id,
            role="user",
            content=user_query
        )
        db.add(user_msg)
        await db.commit()

    try:
        # 2. Chạy LangGraph với PostgresSaver
        async with get_checkpoint_saver() as checkpointer:
            graph_app = build_graph(checkpointer=checkpointer)
            config = {"configurable": {"thread_id": session_id}}
            
            final_state = initial_state.copy()
            node_times = {}
            start_total = time.perf_counter()
            last_step_time = start_total

            async for output in graph_app.astream(initial_state, config=config):
                current_time = time.perf_counter()
                step_duration = (current_time - last_step_time) * 1000
                last_step_time = current_time

                for node_name, state_update in output.items():
                    node_times[node_name] = round(step_duration, 2)
                    logger.info("=" * 60)
                    logger.info(f"👉 STEP FINISHED: {node_name.upper()} ({node_times[node_name]} ms)")
                    logger.info("📦 OUTPUT KẾT QUẢ TỪ AGENT:")
                    for k, v in state_update.items():
                        val_str = str(v)
                        if len(val_str) > 2000:
                            val_str = val_str[:2000] + "... [TRUNCATED]"
                        logger.info(f"  - {k}: {val_str}")
                    logger.info("=" * 60)
                    final_state.update(state_update)

            total_execution_time = round((time.perf_counter() - start_total) * 1000, 2)
            slowest_node = max(node_times, key=node_times.get) if node_times else None

            response = ChatResponse(
                answer=final_state.get("answer", "Hệ thống gặp lỗi, không thể trả lời."),
                answer_format=final_state.get("answer_format", "text"),
                sql=final_state.get("final_sql"),
                data=final_state.get("query_result", []),
                chart_config=final_state.get("chart_config"),
                execution_time_ms=final_state.get("execution_time_ms", 0.0),
                total_execution_time=total_execution_time,
                node_execution_times=node_times,
                slowest_node=slowest_node,
                intent=final_state.get("intent", "unknown"),
                error=final_state.get("executor_error"),
                recommend_questions=[], # Sẽ gán sau
            )

            # Sinh câu hỏi gợi ý tiếp theo (dùng history từ state đã hồi phục)
            if num_recommend > 0:
                if "recommend_questions" in final_state and final_state["recommend_questions"]:
                    response.recommend_questions = final_state["recommend_questions"]
                else:
                    try:
                        recommend_questions = await generate_recommend_questions(
                            user_query=user_query,
                            answer=response.answer,
                            history=final_state.get("history", []),
                            num_recommend=num_recommend,
                        )
                        response.recommend_questions = recommend_questions

                    except Exception as rec_err:
                        logger.warning("[Chat] Không thể sinh recommend questions: %s", rec_err)

            # 3. Lưu phản hồi của Assistant vào DB
            async with get_internal_db_context() as db:
                asst_msg = Message(
                    conversation_id=session_id,
                    role="assistant",
                    content=response.answer,
                    intent=response.intent,
                    sql_query=response.sql,
                    error_message=response.error,
                    execution_time_ms=response.execution_time_ms,
                    metadata_json={
                        "total_time": total_execution_time,
                        "slowest_node": slowest_node
                    }
                )
                db.add(asst_msg)
                await db.commit()

            # Ghi log ra Google Sheet (chạy nền)
            settings = get_settings()
            if settings.google_sheet_url:
                row_data = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    session_id,
                    user_query,
                    str(response.answer),
                    str(response.sql) if response.sql else "",
                    str(response.error) if response.error else ""
                ]
                import asyncio
                asyncio.create_task(append_to_sheet(settings.google_sheet_url, row_data))

            return response

    except Exception as e:
        logger.error("Error during graph execution: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    logger.info(
        "Received chat query: %r (session=%s, history_len=%d, num_recommend=%d)",
        request.query, request.session_id, len(request.history), request.num_recommend,
    )
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "retry_count": 0,
        "history": [m.model_dump() for m in request.history],
        "num_recommend": request.num_recommend,
    }
    return await _process_chat(initial_state)


@router.post("/qldt/chat", response_model=ChatResponse, tags=["QLDT"])
async def qldt_chat_endpoint(request: ChatRequest) -> ChatResponse:
    logger.info(
        "Received QLDT chat query: %r (session=%s, history_len=%d, num_recommend=%d)",
        request.query, request.session_id, len(request.history), request.num_recommend,
    )
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "retry_count": 0,
        "history": [m.model_dump() for m in request.history],
        "num_recommend": request.num_recommend,
        "domain": "qldt",
    }
    return await _process_chat(initial_state)


@router.post("/tcns/chat", response_model=ChatResponse, tags=["TCNS"])
async def tcns_chat_endpoint(request: ChatRequest) -> ChatResponse:
    logger.info(
        "Received TCNS chat query: %r (session=%s, history_len=%d, num_recommend=%d)",
        request.query, request.session_id, len(request.history), request.num_recommend,
    )
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "retry_count": 0,
        "history": [m.model_dump() for m in request.history],
        "num_recommend": request.num_recommend,
        "domain": "tcns",
    }
    return await _process_chat(initial_state)


@router.post("/chat_with_table", response_model=ChatResponse)
async def chat_with_table_endpoint(request: ChatWithTableRequest) -> ChatResponse:
    logger.info(
        "Received chat_with_table query: %r (session=%s, tables=%s, history_len=%d, num_recommend=%d)",
        request.query, request.session_id, request.selected_tables,
        len(request.history), request.num_recommend,
    )
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "selected_tables": request.selected_tables,
        "retry_count": 0,
        "history": [m.model_dump() for m in request.history],
        "num_recommend": request.num_recommend,
    }
    return await _process_chat(initial_state)


@router.post("/qldt/chat_with_table", response_model=ChatResponse, tags=["QLDT"])
async def qldt_chat_with_table_endpoint(request: ChatWithTableRequest) -> ChatResponse:
    logger.info(
        "Received QLDT chat_with_table query: %r (session=%s, tables=%s, history_len=%d, num_recommend=%d)",
        request.query, request.session_id, request.selected_tables,
        len(request.history), request.num_recommend,
    )
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "selected_tables": request.selected_tables,
        "retry_count": 0,
        "history": [m.model_dump() for m in request.history],
        "num_recommend": request.num_recommend,
        "domain": "qldt",
    }
    return await _process_chat(initial_state)


@router.post("/tcns/chat_with_table", response_model=ChatResponse, tags=["TCNS"])
async def tcns_chat_with_table_endpoint(request: ChatWithTableRequest) -> ChatResponse:
    logger.info(
        "Received TCNS chat_with_table query: %r (session=%s, tables=%s, history_len=%d, num_recommend=%d)",
        request.query, request.session_id, request.selected_tables,
        len(request.history), request.num_recommend,
    )
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "user_id": request.user_id,
        "selected_tables": request.selected_tables,
        "retry_count": 0,
        "history": [m.model_dump() for m in request.history],
        "num_recommend": request.num_recommend,
        "domain": "tcns",
    }
    return await _process_chat(initial_state)
