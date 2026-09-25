# HỆ THỐNG NL2SQL & TEXT-TO-DASHBOARD (AI DATA ASSISTANT)

Hệ thống cung cấp tính năng hỏi đáp thông minh với dữ liệu (Data Q&A). Cho phép người dùng đặt câu hỏi bằng ngôn ngữ tự nhiên (đặc biệt tối ưu cho Tiếng Việt), sau đó hệ thống sẽ tự động: hiểu ý định, trích xuất cấu trúc DB liên quan, tạo mã SQL chính xác, thực thi trên PostgreSQL, và tự động quyết định trả về dưới dạng Text tổng hợp, Bảng biểu (Table) hoặc Biểu đồ (Chart).

## TỔNG QUAN KIẾN TRÚC & CÔNG NGHỆ CHÍNH

Hệ thống được thiết kế theo kiến trúc **Mạng lưới Đa Tác Nhân (Multi-Agent System)** dựa trên **Mô hình Đồ Thị (StateGraph)** sử dụng **LangGraph**. Mỗi thao tác phân tích được đảm nhiệm bởi một "Agent" (Node) chuyên biệt, phối hợp thông tin qua state chung `AgentState`.

*   **LLM Engine:** OpenAI API (`gpt-4o-mini`).
*   **Orchestration:** LangChain & LangGraph (Quản lý luồng multi-agents, theo dõi tiến trình state).
*   **Vector Database:** Qdrant (Lập chỉ mục và truy xuất Schema & Truy vấn mẫu/Few-shot).
*   **Cơ Sở Dữ Liệu Thực Thi:** Đa nguồn qua **Domain Registry** — mỗi domain (`qldt`, `tcns`) tự khai engine riêng (PostgreSQL qua `asyncpg`, hoặc ClickHouse qua HTTP driver). Xem `config.DomainConfig`.
*   **Web Framework (API):** FastAPI (Hỗ trợ cấu trúc Asynchronous API).

---

## CƠ CHẾ HOẠT ĐỘNG: QUY TRÌNH XỬ LÝ ĐA TÁC NHÂN TỪNG BƯỚC

Mỗi truy vấn đi qua sơ đồ LangGraph gồm các node sau. Một câu hỏi dữ liệu thông thường tốn **3 lượt gọi LLM** (`router`, `sql_gen`, `answer`) và kết thúc trong ~7–11s.

### 0. FAQ (không LLM)
So khớp câu hỏi với `faq_collection` trên Qdrant. Trúng (score ≥ 0.70) → trả lời ngay, kết thúc.

### 1. Router (1 LLM)
Một lượt gọi structured output trả về đồng thời:
*   **`domain`** — cơ sở dữ liệu cần dùng (`qldt` / `tcns`), chỉ hỏi LLM khi endpoint chung `/chat` được gọi và registry có > 1 domain. Các endpoint `/qldt/chat`, `/tcns/chat` gán domain sẵn.
*   **`intent`** — `data_query`, `chart_request`, `schema_question`, `knowledge_query`, `domain_query`, `greeting`, `out_of_scope`, `ambiguous`.
*   **`clarification_question`** — khi `ambiguous`, router đặt luôn câu hỏi làm rõ vào `answer` và kết thúc.
*   **Điều hướng:** `data_query` / `chart_request` / `domain_query` ➔ **Schema** + **Knowledge** (song song); `schema_question` ➔ Schema; `knowledge_query` ➔ Knowledge; `greeting` / `out_of_scope` ➔ Answer (câu soạn sẵn, không LLM).

### 2. Schema Agent & Knowledge Agent (song song)
*   **Schema:** semantic search trên `schema_collection_<domain>` lấy bảng liên quan (tên bảng, mô tả, cột, FK, sample). Có fallback LLM khi vector search không đủ bảng.
*   **Knowledge:** RAG quy định nghiệp vụ từ `knowledge_collection`. Với `knowledge_query` node này tự sinh câu trả lời và kết thúc; với các intent khác nó chỉ nạp `business_context` cho bước sinh SQL.

### 3. SQL Generation (1 LLM)
Một lượt gọi structured output gồm hai field theo thứ tự: **`plan`** (kế hoạch 6 bước: bảng → cột → lọc → JOIN → tổng hợp → sắp xếp, có ràng buộc *không tự thêm điều kiện lọc*) rồi **`sql`**. Prompt kèm schema, quy định nghiệp vụ, 3 ví dụ few-shot gần nghĩa nhất từ `few_shot_collection_<domain>`, và khối quy tắc theo dialect (`prompts/dialect.py`).

### 4. SQL Check (không LLM)
Chốt chặn lệnh ghi (regex) + `EXPLAIN` dry-run trên đúng engine của domain. Lỗi ➔ thông báo lỗi của DB được đưa nguyên về **SQL Generation** để sinh lại (tối đa 3 lần). Hết lượt ➔ Answer báo không tạo được truy vấn.

### 5. Executor (không LLM)
Chạy SQL, cache Redis theo `(engine, domain, db, sql)`, giới hạn 1000 dòng, log EXPLAIN ANALYZE cho query chậm.

### 5b. Data Check (không LLM)
Kiểm định kết quả: lỗi thực thi, 0 dòng, một ô NULL, toàn NULL ➔ đẩy về SQL Generation kèm lý do, **tối đa 1 lần** (0 dòng đôi khi là câu trả lời đúng).

### 6. Chart (không LLM, trừ khi người dùng xin biểu đồ)
Chọn kiểu biểu đồ và trục bằng luật từ `column_profiles` (1 ô số → `number`; cột thời gian + số → `line`; hỏi "tỉ lệ" và ≤ 8 nhóm → `pie`; dimension + số → `bar`; 2 số → `scatter`; còn lại `table`). Chỉ gọi LLM khi intent là `chart_request` (hoặc API ép chart) **và** dữ liệu có nhiều cách map trục.

### 7. Answer (1 LLM, stream)
Viết câu trả lời text thuần bằng tiếng Việt và stream từng token ra client. `answer_format` (`text` / `table` / `chart+text`) được tính bằng luật từ `chart_config` và số dòng.

---

## CẤU TRÚC THƯ MỤC DỰ ÁN (FOLDER STRUCTURE)

*   📁 `agents/`: Chứa logic từng LangGraph Node (vd: `router_agent.py`, `sql_gen_agent.py`,...).
*   📁 `api/`: Lớp Web Framework mở bằng FastAPI. Chứa các `routers` API (Chat, Database Schemas, Chart).
*   📁 `graph/`: Định nghĩa sườn Mạng lưới Đa Tác Nhân sử dụng LangGraph (`builder.py`, thiết lập biến số chia sẻ trong `state.py`).
*   📁 `prompts/`: Tổng hợp các tập lệnh cho từng tính cách Prompting của từng LLM Agent.
*   📁 `db/`: Tích hợp các module giao tiếp Database/VectorDB (`connection.py`), `seeds` (dữ liệu ban đầu) và tính năng Database Migration (alembic).
*   📁 `scripts/`: Chứa các tệp chạy script (ví dụ: `export_schema.py`, chạy benchmark, v.v).
*   📁 `static/`: Tệp UI tĩnh, chứa giao diện dạng Web Frontend để test (HTML/JS/CSS).
*   📄 `main.py`: Tệp gốc chạy uvicorn FastAPI server.
*   📄 `config.py`: Tệp setting cấu hình chung xử lý `.env`.

Xin cảm ơn vì đã sử dụng Hệ thống AI Data Assistant này!
