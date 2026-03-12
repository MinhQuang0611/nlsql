from typing import Optional, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi ngôn ngữ tự nhiên từ người dùng")
    session_id: str = Field("default", description="ID của phiên chat để theo dõi context (tuỳ chọn)")

class ChatWithTableRequest(ChatRequest):
    selected_tables: list[str] = Field(..., description="Danh sách các bảng giới hạn truy vấn")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời cuối bằng ngôn ngữ tự nhiên")
    answer_format: str = Field("text", description="Định dạng trả lời gợi ý: text, table, chart+text")
    sql: Optional[str] = Field(None, description="Câu lệnh SQL đã sử dụng (ẩn với user thông thường, hữu ích cho debug)")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Dữ liệu thô từ database (nếu có)")
    chart_config: Optional[dict[str, Any]] = Field(None, description="Cấu hình biểu đồ (nếu có)")
    execution_time_ms: float = Field(0.0, description="Thời gian thực thi SQL")
    intent: str = Field(..., description="Ý định đo được")
    error: Optional[str] = Field(None, description="Thông báo lỗi (nếu có)")
