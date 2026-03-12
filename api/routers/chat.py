import logging
from fastapi import APIRouter, HTTPException
from api.schemas.chat import ChatRequest, ChatWithTableRequest, ChatResponse
from graph.builder import build_graph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])

graph_app = build_graph()

async def _process_chat(initial_state: dict) -> ChatResponse:
    try:
        final_state = initial_state.copy()
        
        async for output in graph_app.astream(initial_state):
            for node_name, state_update in output.items():
                logger.info("=" * 60)
                logger.info(f"👉 STEP FINISHED: {node_name.upper()}")
                logger.info("📦 OUTPUT KẾT QUẢ TỪ AGENT:")
                for k, v in state_update.items():
                    val_str = str(v)
                    if len(val_str) > 2000:
                        val_str = val_str[:2000] + "... [TRUNCATED]"
                    logger.info(f"  - {k}: {val_str}")
                logger.info("=" * 60)
                final_state.update(state_update)
        
        return ChatResponse(
            answer=final_state.get("answer", "Hệ thống gặp lỗi, không thể trả lời."),
            answer_format=final_state.get("answer_format", "text"),
            sql=final_state.get("final_sql"),
            data=final_state.get("query_result", []),
            chart_config=final_state.get("chart_config"),
            execution_time_ms=final_state.get("execution_time_ms", 0.0),
            intent=final_state.get("intent", "unknown"),
            error=final_state.get("executor_error")
        )

    except Exception as e:
        logger.error("Error during graph execution: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    logger.info("Received chat query: %r (session=%s)", request.query, request.session_id)
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "retry_count": 0,
    }
    return await _process_chat(initial_state)

@router.post("/chat_with_table", response_model=ChatResponse)
async def chat_with_table_endpoint(request: ChatWithTableRequest) -> ChatResponse:
    logger.info("Received chat_with_table query: %r (session=%s, tables=%s)", request.query, request.session_id, request.selected_tables)
    initial_state = {
        "user_query": request.query,
        "session_id": request.session_id,
        "selected_tables": request.selected_tables,
        "retry_count": 0,
    }
    return await _process_chat(initial_state)
