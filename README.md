# NL2SQL & Text-to-Dashboard System

Hệ thống cho phép người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên (Tiếng Việt), từ đó hệ thống sẽ tự động hiểu, chuyển đổi thành truy vấn SQL, thực thi trên cơ sở dữ liệu PostgreSQL và trả về câu trả lời dưới dạng Text, Bảng biểu (Table), hoặc Biểu đồ (Chart).

## Lưu đồ hoạt động (System Flow)

Hệ thống được thiết kế theo mô hình **Đồ thị (StateGraph)** sử dụng framework **LangGraph**. Mỗi bước (Node) trong đồ thị là một AI Agent chuyên biệt.

Luồng hoạt động xử lý một truy vấn đi qua các Agent sau:

### 1. `intent_agent` (Phân loại ý định)
- **Nhiệm vụ**: Nhận câu hỏi thô của người dùng và xác định mục đích cốt lõi (`data_query`, `chart_request`, `schema_question`, `greeting`, `out_of_scope`).
- **Điều hướng**: 
  - Nếu là câu chào (`greeting`) hoặc câu ngoài lề (`out_of_scope`), nhảy thẳng tới **`answer_agent`** để trả lời giao tiếp thông thường.
  - Nếu là các yêu cầu truy vấn dữ liệu/biểu đồ, tiếp tục chuyển đến **`schema_agent`**.

### 2. `schema_agent` (Trích xuất & Semantic Search)
- **Nhiệm vụ**: Truy xuất dữ liệu trong cơ sở dữ liệu Vector (Qdrant) để lấy ra Top 8 bảng (tables) có ý nghĩa sát với câu hỏi nhất, tránh việc đưa quá nhiều bảng không cần thiết vào prompt.
- **Context nhúng**: Dữ liệu được đưa vào nhúng (embedding) bao gồm: Tên bảng, Chú thích bảng (Description), Cấu trúc cột, và Các khóa ngoại (Foreign Keys).
- **Điều hướng**: Trừ khi mục đích chỉ là hỏi đáp về thông tin bảng (`schema_question`), hệ thống sẽ tiếp tục chuyển tới **`sql_gen_agent`**.

### 3. `sql_gen_agent` (Tạo truy vấn SQL ngầm)
- **Nhiệm vụ**: Dựa vào câu hỏi, các Table Schema đã được lọc, và thông tin Query mẫu (Few-shot examples từ Qdrant) để viết mã SQL.
- **Cơ chế độ Tin Cậy (Self-Consistency)**: Thuật toán yêu cầu LLM sinh ra 3 câu trả lời (candidates) song song với "nhiệt độ" (temperature) mở rộng. Sau đó hệ thống sử dụng cơ chế bỏ phiếu majority voting (VD: 3/3 hoặc 2/3) để tự động chọn ra câu SQL chính xác nhất.

### 4. `sql_check_agent` (Kiểm định Syntax tĩnh)
- **Nhiệm vụ**: Kiểm thử tính hợp lệ của câu lệnh truy vấn mà không trực tiếp làm thay đổi/hoặc lấy dữ liệu DB. Nó sử dụng chức năng `EXPLAIN` của PostgreSQL.
- **Điều hướng**:
  - **Hợp lệ (Valid)**: Chuyển tới **`execute`** node.
  - **Có lỗi (Invalid)**: Báo lỗi ngược lại (Feedback) cho **`sql_gen_agent`** để LLM viết và sửa lại câu lệnh. Giới hạn tối đa sửa lỗi là 3 lần. Nếu vượt quá số lần, hệ thống dừng lại và vẫn đi tới `execute` (báo failed).

### 5. `executor_agent` (Thực thi truy vấn)
- **Nhiệm vụ**: Gửi kết nối DB và chạy câu SQL hoàn thiện cuối cùng trên PostgreSQL, đồng thời ghi nhận kết quả dữ liệu thô (raw records), số lượng bản ghi và thời gian thực thi thuật toán.

### 6. `chart_agent` (Xây dựng cấu hình Biểu đồ)
- **Nhiệm vụ**: Nếu người dùng gọi ý định `chart_request` (VD: "Vẽ biểu đồ hình tròn..."), Node này sẽ đọc mô tả và kết quả trả về từ DB để suy ra Cấu hình biểu đồ (Chart Config) đúng nhất, quy định cách map Dữ liệu ra Trục X, Trục Y trên frontend.

### 7. `answer_agent` (Tổng hợp Kết quả trả về)
- **Nhiệm vụ**: Biên dịch tất cả những dữ liệu máy tính (raw data) hoặc cấu hình nhận được thành câu trả lời Tiếng Việt thân thiện, rõ ràng, gãy gọn để trả về cho người dùng (Format: Text, Table layout, hoặc Chart). 
- Đóng luồng quy trình (Kích hoạt **END**).

---

## Các Công Nghệ Cốt Lõi
- **LLM Engine**: OpenAI API (`gpt-4o-mini`).
- **Orchestration**: LangChain & LangGraph (Quản lý luồng multi-agents).
- **Vector Database**: Qdrant (Lập chỉ mục và truy xuất Schema & Few-shot).
- **RDBMS**: PostgreSQL kết nối bất đồng bộ qua `asyncpg` và `SQLAlchemy`.
- **Backend**: FastAPI.
