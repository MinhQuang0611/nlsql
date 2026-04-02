# Tài liệu Kiến trúc Chatbot NLSQL (v2.0)

Tài liệu này chi tiết về việc tích hợp **Persistence**, **Chat History**, và **Knowledge Agent** vào hệ thống NLSQL.

---

## 1. Quản lý Hội thoại & Lịch sử (Persistence)

Hệ thống sử dụng **LangGraph PostgresSaver** để lưu trữ trạng thái của hội thoại một cách bền vững.

### Cơ chế hoạt động:
- **`session_id` (Thread ID)**: Mỗi phiên hội thoại được định danh bằng một `session_id`. ID này được ánh xạ trực tiếp thành `thread_id` trong LangGraph.
- **Tự động khôi phục ngữ cảnh**: Khi người dùng gửi câu hỏi mới với cùng `session_id`, LangGraph sẽ tự động tải trạng thái trước đó (bao gồm lịch sử tin nhắn, biến trạng thái) từ Postgres.
- **Lưu trữ nhị phân**: Các checkpoint (trạng thái đồ thị) được lưu trong các bảng như `checkpoint_blobs` và `checkpoint_writes` dưới dạng binary.

### Database Schema (sqlalchemy):
Chúng tôi cũng duy trì các bảng quan hệ để phục vụ việc tra cứu và quản lý tin nhắn tường minh:
- **`conversations`**: Lưu thông tin phiên chat (ID, User_ID, Title, Timestamps).
- **`messages`**: Lưu chi tiết từng lượt trao đổi. Lưu trữ các thông tin quan trọng như:
    - `role`: user/assistant.
    - `intent`: Ý định của người dùng (knowledge_query, domain_query, ...).
    - `sql_query`: Câu lệnh SQL được sinh ra.
    - `execution_time_ms`: Thời gian thực hiện query.
    - `content`: Nội dung tin nhắn.

---

## 2. Knowledge Agent (RAG)

Knowledge Agent giúp Chatbot trả lời các câu hỏi về nghiệp vụ dựa trên tài liệu (không phụ thuộc vào CSDL hành chính).

### Chức năng:
- **Retriever**: Sử dụng **Qdrant** làm Vector Database để tìm kiếm các đoạn văn bản liên quan dựa trên Embedding.
- **Intent Handling**:
    1. **`knowledge_query`**: Trả lời trực tiếp từ tài liệu kiến thức.
    2. **`domain_query`**: Trích xuất kiến thức liên quan để bổ sung ngữ cảnh cho bước sinh SQL (giúp SQL Planner hiểu các quy tắc nghiệp vụ phức tạp).

### Quản lý Tri thức:
- Tri thức được đồng bộ từ **Google Sheets** hoặc tệp cục bộ.
- Chạy script `scripts/index_knowledge.py` để cập nhật dữ liệu vào Qdrant.

---

## 3. Quy trình Khởi động & Migrations

Hệ thống đã được tối ưu hóa để tự động chuẩn bị môi trường:
- **Lifespan Startup**: Khi ứng dụng khởi chạy, nó gọi `init_internal_db()`.
- **Auto-Migration**: Hệ thống sẽ tự động tạo các bảng SQLAlchemy và chạy lệnh `checkpointer.setup()` để khởi tạo các bảng checkpoint của LangGraph.
- **Transaction Safety**: Quá trình khởi tạo checkpoint được chạy trong chế độ `autocommit` để tránh xung đột với các logic giao dịch SQL thông thường.

---

## 4. Hướng dẫn tích hợp Frontend

Frontend chỉ cần gửi tối thiểu:
```json
{
  "query": "Câu hỏi của bạn",
  "session_id": "ID_phien_chat",
  "user_id": "ID_nguoi_dung (tùy chọn)"
}
```
**Lưu ý**: Không bắt buộc phải gửi liên tục mảng `history` vì Backend đã tự quản lý lịch sử thông qua `session_id`.

---

> [!TIP]
> Bạn có thể theo dõi logic chi tiết tại `api/routers/chat.py` và `db/models/chat_history.py`.
