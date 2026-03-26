# HỆ THỐNG NL2SQL & TEXT-TO-DASHBOARD (AI DATA ASSISTANT)

Hệ thống cung cấp tính năng hỏi đáp thông minh với dữ liệu (Data Q&A). Cho phép người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên (đặc biệt tối ưu cho Tiếng Việt), sau đó hệ thống sẽ tự động: hiểu ý định, trích xuất cấu trúc DB liên quan, tạo mã SQL chính xác, thực thi trên PostgreSQL, và tự động quyết định trả về dưới dạng Text tổng hợp, Bảng biểu (Table) hoặc Biểu đồ (Chart).

## TỔNG QUAN KIẾN TRÚC & CÔNG NGHỆ CHÍNH

Hệ thống được thiết kế theo kiến trúc **Mạng lưới Đa Tác Nhân (Multi-Agent System)** dựa trên **Mô hình Đồ Thị (StateGraph)** sử dụng **LangGraph**. Mỗi thao tác phân tích được đảm nhiệm bởi một "Agent" (Node) chuyên biệt, phối hợp thông tin qua state chung `AgentState`.

*   **LLM Engine:** OpenAI API (`gpt-4o-mini`).
*   **Orchestration:** LangChain & LangGraph (Quản lý luồng multi-agents, theo dõi tiến trình state).
*   **Vector Database:** Qdrant (Lập chỉ mục và truy xuất Schema & Truy vấn mẫu/Few-shot).
*   **Cơ Sở Dữ Liệu Thực Thi:** PostgreSQL (Kết nối bất đồng bộ qua `asyncpg` và `SQLAlchemy`).
*   **Web Framework (API):** FastAPI (Hỗ trợ cấu trúc Asynchronous API).

---

## CƠ CHẾ HOẠT ĐỘNG: QUY TRÌNH XỬ LÝ ĐA TÁC NHÂN TỪNG BƯỚC

Mỗi truy vấn đi qua sơ đồ LangGraph gồm các bước chính sau. Từ một người dùng gửi lệnh Chat, trạng thái (State) sẽ tuần tự truyền qua cho tới khi hoàn tất (`END`).

### 1. Phân loại Ý Định (Intent Agent)
*   **Nhiệm vụ:** Là điểm bắt đầu (`START`). Agent này nhận câu hỏi thô từ người dùng và phân tích ý định để quyết định luồng đi tiếp theo.
*   **Các loại Ý Định:**
    *   `data_query`: Truy vấn lấy số liệu, dữ liệu bảng.
    *   `chart_request`: Yêu cầu vẽ biểu đồ (vd: "Vẽ biểu đồ tròn hiển thị...").
    *   `schema_question`: Câu hỏi về kiến trúc dữ liệu (vd: "Bảng nào chứa sinh viên?").
    *   `ambiguous`: Câu hỏi mơ hồ, thiếu thông tin chuyên môn.
    *   `greeting`: Câu chào hỏi thông thường.
    *   `out_of_scope`: Câu hỏi không liên quan tới hệ thống dữ liệu.
*   **Cơ chế Điều Hướng (Routing):**
    *   `data_query`, `chart_request`, `schema_question` ➔ Chuyển qua **Schema Agent**.
    *   `ambiguous` ➔ Chuyển sang **Clarification Agent** để xin làm rõ.
    *   `greeting`, `out_of_scope` ➔ Chuyển thẳng về **Answer Agent** (Bỏ qua truy vấn cơ sở dữ liệu).

### 2. Trích xuất Ngữ Cảnh Dữ Liệu (Schema Agent)
*   **Nhiệm vụ:** Tìm cấu trúc Table (Bảng) phù hợp với yêu cầu để không nhồi nhét toàn bộ database vào prompt của LLM gây nhiễu loạn.
*   **Cơ chế Sematic Search:** Hệ thống sử dụng tìm kiếm qua Vector Database (Qdrant) để lấy Top các bảng sát nghĩa với câu hỏi nhất, bao gồm Tên bảng, Chức năng (Description), Cấu trúc cột, và Các Foreign Keys.
*   **Điều Hướng:** 
    *   Trừ trường hợp ý định chỉ là `schema_question` (chuyển thẳng tới **Answer Agent** để giải đáp), hệ thống sẽ chuyển cấu trúc (schemas) này sang cho **SQL Generation Agent**.

### 3. Tạo Sinh SQL (SQL Generation Agent)
*   **Nhiệm vụ:** Viết các câu SQL thô từ Text thông qua dữ kiện Schema đã trích xuất, có đính kèm thêm các Query Mẫu (Few-shot) để AI bắt chước tư duy.
*   **Cơ chế Self-Consistency:** Không chỉ tạo một kết quả, nó sẽ tạo ra nhiều phiên bản câu truy vấn SQL khác nhau trong cùng một lúc, đọ chéo (majority voting) độ tin cậy để chọn lọc được câu lệnh tốt nhất. 
*   **Điều Hướng:** Chuyển câu truy vấn tới kiểm định ở **SQL Check Agent**.

### 4. Kiểm Định Cú Pháp SQL (SQL Check Agent)
*   **Nhiệm vụ:** Kiểm tra "về mặt tĩnh" xem câu SQL có chạy được không (Syntax check) mà không sửa đổi dữ liệu (vd: Dùng hàm `EXPLAIN ...` trên PostgreSQL).
*   **Phản Vệ (Self-Correction):** 
    *   Nếu SQL bị sai (Invalid), nhận Error Log từ Engine Database và trả lại cho **SQL Generation Agent** sửa đổi (Self-Refine). Giới hạn tối đa là 3 lần sửa.
    *   Nếu SQL đúng (Hợp lệ), chuyển tới **Executor Agent**.

### 5. Thực thi Cơ Sở Dữ Liệu (Executor Agent)
*   **Nhiệm vụ:** Thiết lập kết nối Asyncới PostgreSQL và thi hành truy vấn bằng lệnh SQL hoàn chỉnh. Thu thập kết quả dưới dang dictionary `List[Dict[str, Any]]`, đo lường thời gian (execution_time_ms) và đếm tổng số dòng (row_count).
*   **Điều Hướng:** Đi tới **Chart Agent**.

### 6. Xử lý & Khởi tạo Biểu Đồ (Chart Agent)
*   **Nhiệm vụ:** Nếu Intent của người dùng ban đầu rơi vào `chart_request` (Hoặc đôi khi hệ thống tự phán đoán dữ liệu hợp với chart hơn qua cờ `force_chart`).
*   **Cơ chế Mapping:** Đọc dữ liệu thô từ Executor, đồng thời phân nhóm kiểu (Categorical vs Numerical) qua Data Profiling để tự động gán trục X, trục Y, kiểu đồ thị (bar, line, pie, number, table, v.v.). Output là chuẩn `ChartConfig` rõ ràng.

### 7. Phản hồi Thông Minh (Answer Agent) & Làm rõ (Clarification Agent)
*   **Answer Agent:** Đóng vai trò tổng kết. Tổng hợp thông tin từ chuỗi quá trình: Bảng Raw Data của DB, hoặc Setup Biểu Đồ của Chart Agent để định dạng format `text`, `table` hoặc `chart+text` trả về cho Interface của user với ngôn từ chuyên nghiệp. **(Hoàn thành & END)**.
*   **Clarification Agent:** Nằm ngoài luồng dữ liệu, nếu Intent Agent phát hiện `ambiguous` (Mơ hồ), Agent này lấy yêu cầu và tự đặt ra câu hỏi ngược lại yêu cầu sự giải thích (Clarification question) cho người dùng.

---

## CẤU TRÚC THƯ MỤC DỰ ÁN (FOLDER STRUCTURE)

*   📁 `agents/`: Chứa kịch bản & logic khởi chạy từng LangGraph Node (vd: `intent_agent.py`, `sql_gen_agent.py`,...).
*   📁 `api/`: Lớp Web Framework mở bằng FastAPI. Chứa các `routers` API (Chat, Database Schemas, Chart).
*   📁 `graph/`: Định nghĩa sườn Mạng lưới Đa Tác Nhân sử dụng LangGraph (`builder.py`, thiết lập biến số chia sẻ trong `state.py`).
*   📁 `prompts/`: Tổng hợp các tập lệnh cho từng tính cách Prompting của từng LLM Agent.
*   📁 `db/`: Tích hợp các module giao tiếp Database/VectorDB (`connection.py`), `seeds` (dữ liệu ban đầu) và tính năng Database Migration (alembic).
*   📁 `scripts/`: Chứa các tệp chạy script (ví dụ: `export_schema.py`, chạy benchmark, v.v).
*   📁 `static/`: Tệp UI tĩnh, chứa giao diện dạng Web Frontend để test (HTML/JS/CSS).
*   📄 `main.py`: Tệp gốc chạy uvicorn FastAPI server.
*   📄 `config.py`: Tệp setting cấu hình chung xử lý `.env`.

Xin cảm ơn vì đã sử dụng Hệ thống AI Data Assistant này!
