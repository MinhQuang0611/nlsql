from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


VALID_CHART_TYPES = {"bar", "line", "pie", "table", "number", "scatter"}


class ChartRequest(BaseModel):
    user_query: str = Field(..., description="Câu hỏi gốc của người dùng (dùng để agent hiểu ngữ cảnh)")
    data: list[dict[str, Any]] = Field(..., description="Data thô từ database (query_result)")
    chart_type: Optional[str] = Field(
        None,
        description=(
            "Loại biểu đồ mong muốn (tuỳ chọn). "
            "Nếu không truyền, agent tự chọn chart type phù hợp nhất. "
            f"Các giá trị hợp lệ: {sorted(VALID_CHART_TYPES)}"
        ),
    )


class ChartResponse(BaseModel):
    chart_type: str = Field(..., description="Loại biểu đồ được chọn")
    chart_config: dict[str, Any] = Field(..., description="Full cấu hình biểu đồ (title, x_axis, y_axis, group_by, ...)")
    chart_data: list[dict[str, Any]] = Field(..., description="Data đã được reshape phù hợp với chart type")


class ChatToChartRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi ngôn ngữ tự nhiên của người dùng")
    session_id: str = Field("default", description="ID phiên chat để theo dõi context (tuỳ chọn)")
    chart_type: Optional[str] = Field(
        None,
        description=(
            "Gợi ý loại biểu đồ (tuỳ chọn). "
            "Nếu không truyền, agent tự chọn. "
            f"Các giá trị hợp lệ: {sorted(VALID_CHART_TYPES)}"
        ),
    )


class ChatToChartResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời cuối bằng ngôn ngữ tự nhiên")
    answer_format: str = Field("chart+text", description="Định dạng trả lời: text, table, chart+text")
    sql: Optional[str] = Field(None, description="SQL đã thực thi")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Dữ liệu thô từ database")
    chart_config: Optional[dict[str, Any]] = Field(None, description="Cấu hình biểu đồ")
    chart_data: Optional[list[dict[str, Any]]] = Field(None, description="Data đã reshape cho chart")
    chart_type: Optional[str] = Field(None, description="Loại biểu đồ được chọn cuối cùng")
    execution_time_ms: float = Field(0.0, description="Thời gian thực thi SQL (ms)")
    intent: str = Field(..., description="Intent được phát hiện")
    error: Optional[str] = Field(None, description="Thông báo lỗi nếu có")
