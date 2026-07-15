from typing import Optional, Any
from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: str = Field(..., description="Vai trò: 'user' hoặc 'assistant'")
    content: str = Field(..., description="Nội dung tin nhắn")
    intent: Optional[str] = Field(None, description="Ý định của tin nhắn trợ lý")
    sql: Optional[str] = Field(None, description="Câu lệnh SQL đã chạy")
    data: Optional[list[dict]] = Field(None, description="Dữ liệu kết quả")


class ChatRequest(BaseModel):
    query: str = Field(..., description="Câu hỏi ngôn ngữ tự nhiên từ người dùng")
    session_id: str = Field("default", description="ID của phiên chat để theo dõi context (tuỳ chọn)")
    user_id: Optional[str] = Field(None, description="ID của người dùng (tuỳ chọn, dùng để quản lý hội thoại)")
    history: list[HistoryMessage] = Field(default_factory=list, description="Lịch sử hội thoại (tuỳ chọn, nếu gửi sẽ ghi đè context hiện tại)")
    num_recommend: int = Field(3, ge=0, le=10, description="Số lượng câu hỏi gợi ý tiếp theo (0 để tắt)")


class ChatWithTableRequest(ChatRequest):
    selected_tables: list[str] = Field(..., description="Danh sách các bảng giới hạn truy vấn")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời cuối bằng ngôn ngữ tự nhiên")
    answer_format: str = Field("text", description="Định dạng trả lời gợi ý: text, table, chart+text")
    sql: Optional[str] = Field(None, description="Câu lệnh SQL đã sử dụng (ẩn với user thông thường, hữu ích cho debug)")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Dữ liệu thô từ database (nếu có)")
    chart_config: Optional[dict[str, Any]] = Field(None, description="Cấu hình biểu đồ (nếu có)")
    execution_time_ms: float = Field(0.0, description="Thời gian thực thi SQL")
    total_execution_time: float = Field(0.0, description="Tổng thời gian thực thi toàn bộ graph (ms)")
    node_execution_times: dict[str, float] = Field(default_factory=dict, description="Thời gian thực thi của từng node (ms)")
    slowest_node: Optional[str] = Field(None, description="Node chạy chậm nhất")
    intent: str = Field(..., description="Ý định đo được")
    error: Optional[str] = Field(None, description="Thông báo lỗi (nếu có)")
    recommend_questions: list[str] = Field(default_factory=list, description="Các câu hỏi gợi ý tiếp theo")
    clarification_question: Optional[str] = Field(None, description="Câu hỏi làm rõ (chỉ có khi intent = ambiguous) — client nên hiển thị câu này cho người dùng trả lời")
