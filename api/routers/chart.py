from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from agents.chart_agent import VALID_CHART_TYPES, run_chart_agent
from api.schemas.chart import (
    ChartRequest,
    ChartResponse,
    ChatToChartRequest,
    ChatToChartResponse,
)
from graph.builder import build_graph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chart"])

_graph_app = build_graph()


@router.post(
    "/chart",
    response_model=ChartResponse,
    description=(
        "Nhận data thô (query_result) + câu hỏi của người dùng, "
        "trả về chart_config và chart_data đã được reshape. "
        "Nếu chart_type không được truyền, agent tự chọn loại phù hợp nhất."
    ),
)
async def generate_chart(request: ChartRequest) -> ChartResponse:
    if request.chart_type and request.chart_type not in VALID_CHART_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"chart_type '{request.chart_type}' không hợp lệ. "
                f"Các giá trị hợp lệ: {sorted(VALID_CHART_TYPES)}"
            ),
        )

    logger.info(
        "[ChartRouter] /chart user_query=%r, rows=%d, forced_chart_type=%s",
        request.user_query, len(request.data), request.chart_type,
    )

    try:
        chart_config, chart_data, column_profiles = await run_chart_agent(
            user_query=request.user_query,
            query_result=request.data,
            forced_chart_type=request.chart_type,
        )
    except Exception as exc:
        logger.error("[ChartRouter] /chart error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return ChartResponse(
        chart_type=chart_config["chart_type"],
        chart_config=dict(chart_config),
        chart_data=chart_data,
        column_profiles=column_profiles,
    )


@router.post(
    "/chat_to_chart",
    response_model=ChatToChartResponse,
    description=(
        "Chạy toàn bộ pipeline từ input -> chart: "
        "Nếu chart_type được truyền, agent sẽ ưu tiên dùng loại biểu đồ đó."
    ),
)
async def chat_to_chart(request: ChatToChartRequest) -> ChatToChartResponse:
    # Validate chart_type nếu có
    if request.chart_type and request.chart_type not in VALID_CHART_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"chart_type '{request.chart_type}' không hợp lệ. "
                f"Các giá trị hợp lệ: {sorted(VALID_CHART_TYPES)}"
            ),
        )

    logger.info(
        "[ChartRouter] /chat_to_chart query=%r, session=%s, forced_chart_type=%s",
        request.query, request.session_id, request.chart_type,
    )

    initial_state: dict = {
        "user_query": request.query,
        "session_id": request.session_id,
        "retry_count": 0,
    }
    if request.chart_type:
        initial_state["forced_chart_type"] = request.chart_type

    try:
        final_state = initial_state.copy()
        async for output in _graph_app.astream(initial_state):
            for node_name, state_update in output.items():
                logger.info("=" * 60)
                logger.info("👉 STEP: %s", node_name.upper())
                for k, v in state_update.items():
                    val_str = str(v)
                    if len(val_str) > 2000:
                        val_str = val_str[:2000] + "... [TRUNCATED]"
                    logger.info("  - %s: %s", k, val_str)
                logger.info("=" * 60)
                final_state.update(state_update)

        chart_config = final_state.get("chart_config")
        chart_type_out = chart_config.get("chart_type") if chart_config else None

        return ChatToChartResponse(
            answer=final_state.get("answer", "Hệ thống gặp lỗi, không thể trả lời."),
            answer_format=final_state.get("answer_format", "chart+text"),
            sql=final_state.get("final_sql"),
            data=final_state.get("query_result", []),
            chart_config=dict(chart_config) if chart_config else None,
            chart_data=final_state.get("chart_data"),
            chart_type=chart_type_out,
            column_profiles=final_state.get("column_profiles", []),
            execution_time_ms=final_state.get("execution_time_ms", 0.0),
            intent=final_state.get("intent", "unknown"),
            error=final_state.get("executor_error"),
        )

    except Exception as exc:
        logger.error("[ChartRouter] /chat_to_chart error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
