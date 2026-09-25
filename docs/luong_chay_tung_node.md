# nlsql — Luồng chạy từng node (bắt đầu → đầu ra), kèm ví dụ

> Viết theo đúng code tại thời điểm 2026-09-18. Nguồn: `graph/builder.py`, `graph/state.py`, `agents/*.py`, `api/routers/chat.py`.

Câu hỏi ví dụ dùng xuyên suốt tài liệu:

> **"Vẽ biểu đồ số sinh viên theo từng khoa"** — gửi vào `POST /api/v1/chat`, `session_id = "sess-001"`.

---

## 0. Bức tranh tổng thể

```
START
  │
  ▼
[faq] ──── trúng FAQ (score ≥ 0.70) ──────────────────────────────► END
  │ không trúng
  ▼
[domain_router]  chọn DB (qldt / tcns / …)
  │
  ▼
[intent]  phân loại ý định
  ├── ambiguous ─────────────────► [clarification] ──► END
  ├── greeting / out_of_scope ───► [answer] ─────────► END
  ├── schema_question ───────────► [schema] ──┐
  ├── knowledge_query ───────────► [knowledge]┤
  └── data_query / chart_request / domain_query
                    │
            ┌───────┴────────┐   (chạy SONG SONG)
            ▼                ▼
        [schema]        [knowledge]
            └───────┬────────┘
                    ▼
            [retrieval_join]
                    │
      ┌─────────────┴──────────────┐
      │ knowledge_query /          │ còn lại
      │ schema_question            │
      ▼                            ▼
   [answer]                   [sql_plan]
      │                            │
     END                           ▼
                               [sql_gen] ◄──────────────┐◄──────────────┐
                                   │                    │               │
                                   ▼                    │               │
                               [sql_check]              │               │
                                   │                    │               │
                    ┌──────────────┴─────────┐          │               │
                    │ is_valid               │ sai      │               │
                    ▼                        ▼          │               │
                [execute]              [inc_retry] ─────┘ (tối đa 3)    │
                    │                                                   │
                    ▼                                                   │
               [data_check]                                             │
                    │                                                   │
         ┌──────────┴──────────┐                                        │
         │ hợp lệ              │ bất thường                             │
         ▼                     ▼                                        │
      [chart]           [inc_data_retry] ─────────────────────────────►─┘ (tối đa 1)
         │
         ▼
      [answer] ──► END
```

**Cơ chế truyền dữ liệu:** không có node nào gọi trực tiếp node khác. Mọi node đều là một hàm `async def f(state: AgentState) -> dict`, nhận **toàn bộ state** và trả về **dict các khoá muốn ghi**. LangGraph merge dict đó vào state rồi đưa cho node tiếp theo. Cạnh nối (`add_edge`) quyết định "ai chạy sau ai"; hàm điều hướng (`add_conditional_edges`) đọc state để chọn nhánh.

---

## 1. Điểm bắt đầu — HTTP request

**File:** [api/routers/chat.py](../api/routers/chat.py)

### Đầu vào
```json
POST /api/v1/chat
{
  "user_query": "Vẽ biểu đồ số sinh viên theo từng khoa",
  "session_id": "sess-001",
  "user_id": "u123",
  "num_recommend": 3
}
```

### Router làm gì trước khi vào graph
1. Ghi `Conversation` + `Message(role="user")` vào DB nội bộ.
2. Mở checkpointer (`get_checkpoint_saver()`) → graph nhớ được hội thoại theo `thread_id = session_id`.
3. Gọi `graph_app.astream(initial_state, stream_mode=["updates","messages"])`.

### State khởi tạo truyền vào node đầu tiên
```python
{
    "user_query": "Vẽ biểu đồ số sinh viên theo từng khoa",
    "session_id": "sess-001",
    "history": [],          # lịch sử hội thoại nếu có
    "domain": None,         # /chat chung → chưa chốt DB
    "retry_count": 0,
    "data_retry_count": 0,
}
```

### Đầu ra của router (SSE stream)
```
data: {"event":"connected"}
data: {"event":"node_finish","node":"faq","execution_time_ms":412.3,"state_update":{...}}
data: {"event":"node_finish","node":"domain_router",...}
...
data: {"event":"answer_token","token":"Biểu đồ"}
data: {"event":"answer_token","token":" cho thấy"}
...
data: {"event":"final_result","data":{ ...ChatResponse... }}
```

---

## 2. `faq` — FAQAgent

**File:** [agents/faq_agent.py](../agents/faq_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc từ state** | `user_query` |
| **Việc làm** | Embed câu hỏi → tìm trong Qdrant `faq_collection`, limit 4 |
| **Ngưỡng** | `_FAQ_THRESHOLD = 0.70` |
| **Ghi vào state** | Trúng: `intent`, `answer`, `answer_format`, `recommend_questions`. Không trúng: không ghi gì (trả nguyên `state`) |
| **Node tiếp theo** | `route_after_faq`: `intent == "faq_answered"` → `answer`; ngược lại → `domain_router` |

### Mục đích
Chặn sớm những câu hỏi lặp đi lặp lại đã có câu trả lời soạn sẵn, **không tốn một lượt gọi LLM nào** cho cả pipeline phía sau.

### Ví dụ A — TRÚNG FAQ
Câu hỏi: *"Học phí kỳ này đóng khi nào?"*
```python
# state ghi ra
{
  "intent": "faq_answered",
  "answer": "Học phí kỳ 1 năm học 2026-2027 đóng từ 01/09 đến 30/09/2026 qua cổng thanh toán...",
  "answer_format": "text",
  "recommend_questions": [
      "Học phí ngành CNTT là bao nhiêu?",
      "Cách tra cứu công nợ học phí?"
  ]
}
# → đi tới node `answer`
```

### Ví dụ B — KHÔNG TRÚNG (trường hợp của ta)
Câu hỏi: *"Vẽ biểu đồ số sinh viên theo từng khoa"* → điểm cao nhất 0.42 < 0.70.
```python
# state không đổi, chỉ thu được gợi ý phụ (bị bỏ vì best_hit = None)
{}   # → đi tới `domain_router`
```

> ⚠️ **Điểm đáng chú ý trong code:** `route_after_faq` trả `"answer"` khi trúng FAQ, và có một dòng `return END` nằm **sau** `return "answer"` nên không bao giờ chạy được (dead code, `graph/builder.py:22-29`). Hệ quả: câu trả lời FAQ vẫn phải đi qua `answer_agent`. May là `answer_agent` không có nhánh xử lý `intent == "faq_answered"`, nên nó rơi xuống nhánh gọi LLM cuối hàm và **sinh lại câu trả lời**, ghi đè `answer` mà FAQ đã đặt. Nếu muốn FAQ trả nguyên văn, cần cho `route_after_faq` trả `END`.

---

## 3. `domain_router` — DomainRouterAgent

**File:** [agents/domain_router_agent.py](../agents/domain_router_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `domain` (nếu endpoint đã gán), `user_query`, `history` |
| **Ghi** | `domain`, `domain_reasoning` |
| **Node tiếp theo** | Luôn là `intent` (`add_edge` cứng) |

### Mục đích
Hệ thống có nhiều DB (`qldt`, `tcns`, …). Node này chốt **truy vấn sẽ chạy trên DB nào**, vì `schema_agent` phía sau tìm trong collection `schema_collection_{domain}` và introspect đúng DB đó.

### Ba đường đi
1. **Endpoint đã gán sẵn** (`/qldt/chat`) → tôn trọng, **không gọi LLM**.
2. **Chỉ có 1 domain** → gán luôn, **không gọi LLM**.
3. **Endpoint chung `/chat`** → LLM chọn, output có cấu trúc `DomainRouteSchema{domain, reasoning}`.

### Ví dụ (đường 3)
```python
# Đọc vào
{"user_query": "Vẽ biểu đồ số sinh viên theo từng khoa", "domain": None}

# Prompt đưa cho LLM danh sách domain
# - qldt: Cơ sở dữ liệu quản lý đào tạo — sinh viên, lớp, điểm, học phần
# - tcns: Cơ sở dữ liệu tổ chức nhân sự — cán bộ, phòng ban, lương

# Ghi ra
{
  "domain": "qldt",
  "domain_reasoning": "Câu hỏi về số lượng sinh viên theo khoa — thuộc dữ liệu đào tạo."
}
```

**Kết quả mong muốn:** `domain` luôn là một giá trị hợp lệ trong `settings.list_domains()`. Nếu LLM trả sai hoặc lỗi → fallback về `available[0]`, không bao giờ để `domain` rỗng.

---

## 4. `intent` — IntentAgent

**File:** [agents/intent_agent.py](../agents/intent_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `user_query`, `history` |
| **Ghi** | `intent`, `clarification_question` |
| **Node tiếp theo** | `route_after_intent` (xem bảng dưới) |

### Bảng phân nhánh (`route_after_intent`, `graph/builder.py:31-43`)

| `intent` | Node tiếp theo | Ghi chú |
|---|---|---|
| `domain_query` | `["schema", "knowledge"]` | chạy **song song** |
| `data_query` | `["schema", "knowledge"]` | chạy **song song** |
| `chart_request` | `["schema", "knowledge"]` | chạy **song song** |
| `schema_question` | `schema` | chỉ cần cấu trúc bảng |
| `knowledge_query` | `knowledge` | không cần đụng DB |
| `ambiguous` | `clarification` | hỏi lại người dùng |
| `greeting`, `out_of_scope` | `answer` | trả lời soạn sẵn |

### Ví dụ
```python
# Đọc vào
{"user_query": "Vẽ biểu đồ số sinh viên theo từng khoa", "history": []}

# Ghi ra
{
  "intent": "chart_request",
  "clarification_question": None
}
# → fan-out song song sang `schema` VÀ `knowledge`
```

### Ví dụ nhánh mơ hồ
```python
# user_query = "cho tôi xem dữ liệu"
{
  "intent": "ambiguous",
  "clarification_question": "Bạn muốn xem dữ liệu về sinh viên, điểm số hay học phí? Và trong khoảng thời gian nào?"
}
# → `clarification`
```

> ⚠️ Lưu ý: `VALID_INTENTS` trong code có cả `knowledge_query` và `domain_query`, nhưng `IntentClassifierSchema` mô tả cho LLM **không liệt kê hai giá trị này**. LLM vì thế hiếm khi sinh ra chúng — nhánh `knowledge_query` gần như không được kích hoạt trong thực tế.

---

## 5. `schema` — SchemaAgent (nhánh song song 1)

**File:** [agents/schema_agent.py](../agents/schema_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `domain`, `user_query`, `selected_tables` |
| **Ghi** | `relevant_tables`, `schema_context` |
| **Node tiếp theo** | `retrieval_join` |

### Mục đích
Chọn ra **đúng vài bảng liên quan** trong số hàng trăm bảng của DB, kèm đầy đủ cột / kiểu / khoá ngoại / 3 dòng mẫu, để prompt sinh SQL không bị tràn context.

### Ba chế độ
1. **`selected_tables` có sẵn** (người dùng tick bảng trên UI) → introspect thẳng, bỏ qua vector search.
2. **Vector search Qdrant** — collection `schema_collection_{domain}`, `limit=20`, ngưỡng `SCORE_THRESHOLD = 0.68`, dedup giữ hit điểm cao nhất mỗi bảng.
3. **LLM fallback** — kích hoạt khi vector search tìm được **< 2 bảng**: đưa danh sách toàn bộ tên bảng + `settings.TABLE_RULES` cho LLM chọn tối đa 5 bảng.

### Ví dụ
```python
# Đọc vào
{"domain": "qldt", "user_query": "Vẽ biểu đồ số sinh viên theo từng khoa"}

# Log: Tables passed threshold (0.68): sinh_vien=0.812, khoa=0.774

# Ghi ra
{
  "relevant_tables": ["sinh_vien", "khoa"],
  "schema_context": [
    {
      "table_name": "sinh_vien",
      "description": "Bảng danh sách sinh viên toàn trường",
      "columns": [
        {"name": "ma_sv",    "type": "character varying", "nullable": False, "comment": "Mã sinh viên"},
        {"name": "ho_ten",   "type": "character varying", "nullable": False, "comment": "Họ và tên"},
        {"name": "ma_khoa",  "type": "character varying", "nullable": True,  "comment": "Mã khoa quản lý"},
        {"name": "trang_thai","type": "character varying","nullable": True,  "comment": "Đang học / Bảo lưu / Thôi học"}
      ],
      "foreign_keys": [
        {"column_name": "ma_khoa", "foreign_table": "khoa", "foreign_column": "ma_khoa"}
      ],
      "sample_rows": [
        {"ma_sv": "B23CC004", "ho_ten": "Nguyễn Văn A", "ma_khoa": "CNTT", "trang_thai": "Đang học"}
      ]
    },
    {
      "table_name": "khoa",
      "description": "Danh mục khoa",
      "columns": [
        {"name": "ma_khoa",  "type": "character varying", "nullable": False, "comment": "Mã khoa"},
        {"name": "ten_khoa", "type": "character varying", "nullable": False, "comment": "Tên khoa"}
      ],
      "foreign_keys": [],
      "sample_rows": [{"ma_khoa": "CNTT", "ten_khoa": "Công nghệ thông tin"}]
    }
  ]
}
```

> ⚠️ Node này trả về **dict thuần** (`return {"relevant_tables": ..., "schema_context": ...}`), không phải `{**state, ...}`. Đây là cách đúng cho nhánh song song — nếu trả cả state thì hai nhánh `schema` và `knowledge` sẽ ghi đè lẫn nhau khi merge.

---

## 6. `knowledge` — KnowledgeAgent (nhánh song song 2)

**File:** [agents/knowledge_agent.py](../agents/knowledge_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `user_query`, `intent`, `history` |
| **Ghi** | `knowledge_context`, `business_context` (+ `answer`, `answer_format` nếu `intent == "knowledge_query"`) |
| **Node tiếp theo** | `retrieval_join` |

### Mục đích
Nạp **quy tắc nghiệp vụ** (định nghĩa "sinh viên đang học là gì", "kỳ hiện tại tính thế nào") từ Qdrant `knowledge_collection` để SQL sinh ra đúng ngữ nghĩa nghiệp vụ, không chỉ đúng cú pháp.

Ngưỡng rất thấp — `_SCORE_THRESHOLD = 0.01` — tức gần như **luôn lấy hết 5 hit đầu**.

### Hai dạng payload được xử lý
- **Business rule** (có `tu_khoa` + `dinh_nghia_sql_logic`) → format `[Quy tắc nghiệp vụ: {tu_khoa}]`
- **Văn bản Google Sheet** (có `content`/`text`/`title`) → format `[Nguồn: {source}]`

### Ví dụ
```python
# Đọc vào
{"user_query": "Vẽ biểu đồ số sinh viên theo từng khoa", "intent": "chart_request"}

# Ghi ra
{
  "knowledge_context":
      "[Quy tắc nghiệp vụ: sinh viên đang học]\n"
      "Sinh viên đang học = sinh_vien.trang_thai = 'Đang học'. "
      "Không đếm sinh viên đã thôi học hoặc bảo lưu.\n\n"
      "---\n\n"
      "[Nguồn: So_tay_dao_tao_2026.pdf]\n"
      "Mỗi sinh viên chỉ thuộc duy nhất một khoa quản lý tại một thời điểm.",
  "business_context": [
    {"id": "a1f2...", "tu_khoa": "sinh viên đang học",
     "dinh_nghia_sql_logic": "sinh_vien.trang_thai = 'Đang học'. Không đếm SV thôi học/bảo lưu."},
    {"id": "b7c3...", "tu_khoa": "So_tay_dao_tao_2026.pdf",
     "dinh_nghia_sql_logic": "Mỗi sinh viên chỉ thuộc duy nhất một khoa quản lý..."}
  ]
}
```

### Nhánh `knowledge_query` (dừng sớm)
Nếu `intent == "knowledge_query"`, node tự gọi LLM sinh câu trả lời **ngay tại đây**, ghi luôn `answer` + `answer_format`, và `route_after_retrieval` sẽ đưa thẳng tới `answer`.

---

## 7. `retrieval_join` — điểm hợp nhất

**File:** [graph/builder.py:131](../graph/builder.py#L131) — `lambda state: state`

Node rỗng, không xử lý gì. Vai trò duy nhất: **barrier đồng bộ**. LangGraph chỉ chạy node này khi **cả hai** `schema` và `knowledge` đã xong, nên state tại đây chắc chắn đã có đủ `schema_context` lẫn `business_context`.

### `route_after_retrieval`
| `intent` | Node tiếp theo |
|---|---|
| `knowledge_query`, `schema_question` | `answer` |
| còn lại | `sql_plan` |

Ví dụ của ta: `intent = "chart_request"` → **`sql_plan`**.

---

## 8. `sql_plan` — SQLPlanAgent

**File:** [agents/sql_plan_agent.py](../agents/sql_plan_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `user_query`, `schema_context`, `business_context`, `history`, `domain` |
| **Ghi** | `query_plan` (văn bản thuần) |
| **Node tiếp theo** | `sql_gen` (cứng) |

### Mục đích
Tách **suy luận** khỏi **viết cú pháp**. LLM lập kế hoạch bằng tiếng Việt trước (chọn bảng nào, JOIN ra sao, lọc điều kiện gì, nhóm theo cột nào), rồi node sau mới chuyển kế hoạch đó thành SQL. Cách này giảm rõ rệt lỗi JOIN sai khoá.

Node cũng nạp **dialect rules** theo engine của domain (Postgres vs ClickHouse) qua `get_dialect_label()` / `get_dialect_rules()`.

### Ví dụ
```python
# Đọc vào: schema_context (2 bảng) + business_context (2 quy tắc) như trên

# Ghi ra
{
  "query_plan": """
1. Bảng cần dùng: `sinh_vien` (danh sách SV) và `khoa` (tên khoa hiển thị).
2. JOIN: sinh_vien.ma_khoa = khoa.ma_khoa (theo khoá ngoại đã khai báo).
3. Lọc: theo quy tắc nghiệp vụ, chỉ đếm sinh viên đang học
   → WHERE sinh_vien.trang_thai = 'Đang học'.
4. Nhóm: GROUP BY khoa.ten_khoa.
5. Tính: COUNT(sinh_vien.ma_sv) AS so_luong_sinh_vien.
6. Sắp xếp: ORDER BY so_luong_sinh_vien DESC để biểu đồ dễ đọc.
7. Hiển thị tên khoa (ten_khoa) thay vì mã khoa cho thân thiện người dùng.
"""
}
```

**Trường hợp rỗng:** nếu `schema_context` rỗng → ghi `query_plan = "No schema information provided."` và vẫn đi tiếp (SQL sinh ra sẽ hỏng, `sql_check` bắt được).

---

## 9. `sql_gen` — SQLGenAgent

**File:** [agents/sql_gen_agent.py](../agents/sql_gen_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `user_query`, `query_plan`, `schema_context`, `history`, `retry_count`, `data_retry_count`, `sql_correction.issues`, `data_check_issues` |
| **Ghi** | `generated_sql`, `sql_reasoning`, **reset** `sql_correction` và `final_sql` |
| **Node tiếp theo** | `sql_check` (cứng) |

### Mục đích
Chuyển `query_plan` thành câu SQL chạy được, dùng model riêng `settings.sql_gen_model` (có thể mạnh hơn model chung).

### Ba nguồn đầu vào bổ trợ
1. **Few-shot** từ Qdrant `few_shot_collection_{domain}`, `limit=3` — cặp (câu hỏi, SQL) mẫu.
2. **`retry_hint`** gộp lỗi từ **hai nguồn**:
   - `sql_correction.issues` (khi `retry_count > 0`) — lỗi cú pháp/quyền do EXPLAIN bắt.
   - `data_check_issues` (khi `data_retry_count > 0`) — lỗi ngữ nghĩa do kết quả bất thường.
3. **Dialect rules** theo engine.

### Ví dụ — lần chạy đầu (`retry_count = 0`)
```python
# Ghi ra
{
  "generated_sql": """SELECT k.ten_khoa, COUNT(sv.ma_sv) AS so_luong_sinh_vien
FROM sinh_vien sv
JOIN khoa k ON sv.ma_khoa = k.ma_khoa
WHERE sv.trang_thai = 'Đang học'
GROUP BY k.ten_khoa
ORDER BY so_luong_sinh_vien DESC""",
  "sql_reasoning": "JOIN sinh_vien với khoa theo ma_khoa, lọc trạng thái Đang học theo quy tắc nghiệp vụ, đếm theo tên khoa.",
  "sql_correction": {"is_valid": False, "issues": [], "fixed_sql": None},   # reset
  "final_sql": ""                                                           # reset
}
```

### Ví dụ — lần chạy lại (`retry_count = 1`)
Giả sử lần đầu LLM viết nhầm cột `sv.khoa_id`:
```python
# retry_hint đưa vào prompt:
#   Lần trước sinh SQL bị lỗi:
#     - postgres Error: column sv.khoa_id does not exist

# Ghi ra: SQL đã sửa cột thành sv.ma_khoa
```

---

## 10. `sql_check` — SQLCheckAgent

**File:** [agents/sql_check_agent.py](../agents/sql_check_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `generated_sql`, `schema_context`, `domain`, `user_query` |
| **Ghi** | `sql_correction` (`{is_valid, issues, fixed_sql}`), `final_sql` |
| **Node tiếp theo** | `route_after_sql_check` |

### Ba lớp kiểm tra
1. **Hard safety gate** — regex chặn `INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXECUTE|EXEC`. Trúng → chặn ngay, `final_sql = ""`.
2. **EXPLAIN dry-run** — chạy `EXPLAIN {sql}` thật trên DB của domain. Bắt lỗi cú pháp, sai tên cột/bảng, thiếu quyền — **không tốn chi phí thực thi**.
3. **LLM correction** — nếu EXPLAIN lỗi, đưa (câu hỏi + schema tóm tắt + SQL hỏng + thông báo lỗi DB) cho LLM sửa. SQL sửa xong lại đi qua safety gate lần nữa.

### Bảng điều hướng (`route_after_sql_check`)
| Điều kiện | Node tiếp theo |
|---|---|
| `sql_correction.is_valid == True` | `execute` |
| `retry_count >= 3` | `execute` (bỏ cuộc, để executor báo lỗi thật) |
| còn lại | `inc_retry` → `sql_gen` |

### Ví dụ A — PASS
```python
{
  "sql_correction": {"is_valid": True, "issues": [], "fixed_sql": "SELECT k.ten_khoa, COUNT(...)..."},
  "final_sql": "SELECT k.ten_khoa, COUNT(sv.ma_sv) AS so_luong_sinh_vien\nFROM sinh_vien sv\nJOIN khoa k ON sv.ma_khoa = k.ma_khoa\nWHERE sv.trang_thai = 'Đang học'\nGROUP BY k.ten_khoa\nORDER BY so_luong_sinh_vien DESC"
}
# → `execute`
```

### Ví dụ B — FAIL rồi LLM sửa
```python
# EXPLAIN báo: column sv.khoa_id does not exist
{
  "sql_correction": {
    "is_valid": True,
    "issues": ["Cột 'khoa_id' không tồn tại trong bảng sinh_vien; đã đổi thành 'ma_khoa' theo schema."],
    "fixed_sql": "SELECT k.ten_khoa, COUNT(sv.ma_sv) ... ON sv.ma_khoa = k.ma_khoa ..."
  },
  "final_sql": "SELECT k.ten_khoa, COUNT(sv.ma_sv) ... ON sv.ma_khoa = k.ma_khoa ..."
}
# → `execute` (LLM tự tin đã sửa xong, không cần quay lại sql_gen)
```

### Ví dụ C — bị chặn bởi safety gate
```python
# generated_sql chứa "DROP TABLE sinh_vien"
{
  "sql_correction": {"is_valid": False, "issues": ["Dangerous operation detected: DROP"], "fixed_sql": None},
  "final_sql": ""
}
# → retry_count < 3 nên quay lại `inc_retry` → `sql_gen`
```

---

## 11. `inc_retry` / `inc_data_retry` — bộ đếm

**File:** [graph/builder.py:76-80](../graph/builder.py#L76-L80)

Hai node một dòng, chỉ tăng bộ đếm rồi đẩy về `sql_gen`:
```python
def inc_retry(state):      return {"retry_count":      state.get("retry_count", 0) + 1}
def inc_data_retry(state): return {"data_retry_count": state.get("data_retry_count", 0) + 1}
```

Tách thành node riêng (thay vì tăng bên trong agent) để bộ đếm **luôn tăng đúng một lần mỗi vòng lặp**, bất kể agent trả về sớm ở nhánh nào. Đây là thứ bảo đảm vòng lặp hữu hạn.

- `retry_count`: trần **3** (`route_after_sql_check`)
- `data_retry_count`: trần **1** (`MAX_DATA_RETRY` trong `data_check_agent`)

---

## 12. `execute` — ExecutorAgent

**File:** [agents/executor_agent.py](../agents/executor_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `final_sql`, `domain` |
| **Ghi** | `query_result`, `row_count`, `execution_time_ms`, `executor_error` |
| **Node tiếp theo** | `data_check` (cứng) |

### Trình tự xử lý
1. **`final_sql` rỗng?** → trả lỗi `"No valid SQL to execute."` ngay.
2. **Chốt chặn ghi dữ liệu** — regex nguy hiểm, chỉ bỏ qua khi `settings.allow_write_sql = True` (phải bật tường minh, không phụ thuộc `APP_ENV`).
3. **Áp `LIMIT 1000`** nếu SQL chưa có — Postgres bọc subquery, ClickHouse nối thẳng.
4. **Redis cache** — key = `sha256(engine|domain|db_name|sql_fingerprint)`. Lưu ý key tính trên **SQL thật sự chạy**, không phải câu hỏi người dùng, và có cả domain để `/qldt/chat` không ăn cache của `/tcns/chat`. TTL 3600s.
5. **Thực thi** theo engine của domain (`ch_execute` hoặc `AsyncSession`).
6. **Slow query log** — nếu > 2000 ms và là Postgres, chạy thêm `EXPLAIN ANALYZE` ghi vào log.

### Ví dụ — thành công
```python
{
  "query_result": [
    {"ten_khoa": "Công nghệ thông tin", "so_luong_sinh_vien": 3421},
    {"ten_khoa": "Điện tử viễn thông", "so_luong_sinh_vien": 2187},
    {"ten_khoa": "Quản trị kinh doanh", "so_luong_sinh_vien": 1654},
    {"ten_khoa": "An toàn thông tin",   "so_luong_sinh_vien":  892},
    {"ten_khoa": "Kế toán",             "so_luong_sinh_vien":  743}
  ],
  "row_count": 5,
  "execution_time_ms": 84.31,
  "executor_error": None
}
```

### Ví dụ — cache hit
```python
{
  "query_result": [...],      # lấy từ Redis
  "row_count": 5,
  "execution_time_ms": 0.0,   # dấu hiệu nhận biết cache hit
  "executor_error": None
}
```

### Ví dụ — lỗi DB
```python
{
  "query_result": [],
  "row_count": 0,
  "execution_time_ms": 0.0,
  "executor_error": "relation \"sinh_vien_2026\" does not exist"
}
```

---

## 13. `data_check` — DataCheckAgent

**File:** [agents/data_check_agent.py](../agents/data_check_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `query_result`, `row_count`, `executor_error`, `data_retry_count`, `final_sql` |
| **Ghi** | `data_check_is_valid`, `data_check_issues` |
| **Node tiếp theo** | `route_after_data_check` |

### Mục đích — đóng vòng lặp mà EXPLAIN không đóng được
`sql_check` chỉ xác nhận SQL **chạy được**. Một câu JOIN nhầm khoá hoặc WHERE so với enum không tồn tại vẫn qua EXPLAIN trót lọt, rồi trả 0 dòng — và người dùng nhận câu trả lời sai mà hệ thống tưởng là thành công. Node này đọc **kết quả thật** để bắt lỗi ngữ nghĩa đó.

Node này **không gọi LLM** — thuần heuristic, nên gần như miễn phí.

### Bốn tình huống bị đánh dấu lỗi
| Tình huống | Hàm kiểm tra |
|---|---|
| Có `executor_error` | — |
| `row_count == 0` | — |
| Kết quả là 1 ô duy nhất và ô đó NULL | `_is_null_scalar()` |
| Mọi ô trong mọi dòng đều NULL | `_all_values_null()` |

### Cơ chế chống lặp vô hạn
`MAX_DATA_RETRY = 1`. Quan trọng hơn — **0 dòng không phải lúc nào cũng là lỗi**: câu "có sinh viên nào GPA > 3.99 không?" trả 0 dòng chính là câu trả lời đúng. Vì vậy sau 1 lần thử lại, node **tự đặt `is_valid = True`** để chấp nhận kết quả, và `route_after_data_check` chỉ cần đọc cờ này — không có nguy cơ lặp mãi.

### Ví dụ A — PASS
```python
{"data_check_is_valid": True, "data_check_issues": []}
# → `chart`
```

### Ví dụ B — 0 dòng, lần thử đầu (`data_retry_count = 0`)
```python
{
  "data_check_is_valid": False,
  "data_check_issues": [
    "Câu SQL chạy được nhưng trả về 0 dòng. Nguyên nhân thường gặp: JOIN sai khoá "
    "(ví dụ dùng `_id` thay vì khoá nghiệp vụ), điều kiện WHERE so sánh với giá trị "
    "enum không tồn tại, hoặc lọc theo khoảng thời gian không có dữ liệu. "
    "Hãy rà lại điều kiện JOIN và WHERE. Nếu bạn xác định 0 dòng CHÍNH LÀ câu trả lời "
    "đúng, giữ nguyên câu SQL."
  ]
}
# → `inc_data_retry` (data_retry_count = 1) → `sql_gen`
#   sql_gen đọc data_check_issues, đưa vào retry_hint, sinh lại SQL
#   (ví dụ: 'Đang học' không khớp vì DB lưu là 'DANG_HOC')
```

### Ví dụ C — vẫn 0 dòng, lần thứ hai (`data_retry_count = 1`)
```python
# data_retry_count >= MAX_DATA_RETRY → chấp nhận
{
  "data_check_is_valid": True,        # ← bị ép thành True
  "data_check_issues": ["Câu SQL chạy được nhưng trả về 0 dòng..."]
}
# → `chart`, rồi answer_agent diễn giải trung thực rằng không có dữ liệu
```

---

## 14. `chart` — ChartAgent

**File:** [agents/chart_agent.py](../agents/chart_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `user_query`, `query_result`, `forced_chart_type` |
| **Ghi** | `chart_config`, `chart_data`, `column_profiles` |
| **Node tiếp theo** | `answer` (cứng) |

### Trình tự
1. **`query_result` rỗng?** → trả `chart_type = "table"`, `chart_data = []`, không gọi LLM.
2. **Profile cột** (`utils/data_profiler.profile_columns`) — phân tích kiểu dữ liệu, cardinality của từng cột.
3. **LLM chọn chart** — đưa columns + profile + 3 dòng mẫu, nhận JSON `ChartConfig`. Nếu có `forced_chart_type` thì dùng prompt `CHART_HUMAN_FORCED` và **ép đè** kết quả nếu LLM trả khác.
4. **Reshape** (`_reshape_for_chart`) — ánh xạ cột thật sang `x` / `y` / `group`, giữ nguyên các cột còn lại.
5. **Tinh chỉnh** (`utils/chart_adjustment.adjust_chart_data`) — cập nhật `x_label` / `y_label`.

Loại chart hợp lệ: `bar`, `line`, `pie`, `table`, `number`, `scatter`. Parse lỗi → fallback `table`.

### Ví dụ
```python
# Đọc vào: query_result 5 dòng như trên, forced_chart_type = None

# Ghi ra
{
  "chart_config": {
    "chart_type": "bar",
    "x_axis": "ten_khoa",
    "y_axis": "so_luong_sinh_vien",
    "group_by": None,
    "title": "Số lượng sinh viên theo khoa",
    "x_label": "Khoa",
    "y_label": "Số sinh viên"
  },
  "chart_data": [
    {"x": "Công nghệ thông tin", "y": 3421, "ten_khoa": "Công nghệ thông tin", "so_luong_sinh_vien": 3421},
    {"x": "Điện tử viễn thông",  "y": 2187, "ten_khoa": "Điện tử viễn thông",  "so_luong_sinh_vien": 2187},
    {"x": "Quản trị kinh doanh", "y": 1654, "ten_khoa": "Quản trị kinh doanh", "so_luong_sinh_vien": 1654},
    {"x": "An toàn thông tin",   "y":  892, "ten_khoa": "An toàn thông tin",   "so_luong_sinh_vien":  892},
    {"x": "Kế toán",             "y":  743, "ten_khoa": "Kế toán",             "so_luong_sinh_vien":  743}
  ],
  "column_profiles": [
    {"name": "ten_khoa", "dtype": "categorical", "unique_count": 5, "null_count": 0},
    {"name": "so_luong_sinh_vien", "dtype": "numeric", "min": 743, "max": 3421, "null_count": 0}
  ]
}
```

> ⚠️ Node `chart` nằm trên đường đi **bắt buộc** của mọi `data_query`, không chỉ `chart_request` — tức mỗi câu hỏi dữ liệu đều tốn thêm một lượt gọi LLM cho việc chọn biểu đồ. Trường `force_chart` có khai báo trong `AgentState` nhưng `chart_agent` hiện **không đọc tới**.

---

## 15. `answer` — AnswerAgent

**File:** [agents/answer_agent.py](../agents/answer_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `user_query`, `query_result`, `row_count`, `chart_config`, `knowledge_context`, `intent`, `executor_error`, `history` |
| **Ghi** | `answer`, `answer_format` |
| **Node tiếp theo** | `END` |

### Bốn nhánh trả lời soạn sẵn (không gọi LLM)
| `intent` / điều kiện | `answer` |
|---|---|
| `out_of_scope` | "Xin lỗi, câu hỏi này nằm ngoài phạm vi hệ thống..." |
| `greeting` | "Chào bạn! Tôi là trợ lý phân tích dữ liệu..." |
| `schema_question` | `f"Database có các bảng liên quan: {', '.join(relevant_tables)}."` |
| `executor_error` có giá trị | `f"Không thể thực thi truy vấn. Lỗi: {executor_error}"` |

### Nhánh gọi LLM
- Nếu `knowledge_context` có và `intent == "domain_query"` → prompt `DOMAIN_ANSWER_*` (tổng hợp DB + kiến thức nghiệp vụ).
- Ngược lại → prompt `ANSWER_*` thường.

Chỉ đưa **10 dòng đầu** (`_MAX_PREVIEW_ROWS`) vào prompt để tiết kiệm token. LLM trả JSON `{answer, answer_format}`; parse lỗi thì lấy raw text và suy `answer_format` từ việc có chart hay không.

### Ví dụ
```python
# Đọc vào: row_count = 5, chart_config != None

# Ghi ra
{
  "answer": "Toàn trường hiện có 8.897 sinh viên đang học, phân bố ở 5 khoa. "
            "Khoa Công nghệ thông tin dẫn đầu với 3.421 sinh viên (38,5%), "
            "gấp hơn 4,5 lần khoa Kế toán — khoa có ít sinh viên nhất với 743. "
            "Biểu đồ cột bên dưới thể hiện chênh lệch này.",
  "answer_format": "chart+text"
}
# → END
```

**Điểm quan trọng về streaming:** đây là node **duy nhất** mà router bóc token gửi ra client (`meta.get("langgraph_node") != "answer"` → bỏ qua). `JsonStringFieldStreamer("answer")` bóc dần trường `answer` ra khỏi JSON mà LLM đang viết dở, nên người dùng thấy chữ chạy ngay. Bốn nhánh soạn sẵn ở trên **không sinh token nào**, nên router có đường lui: gửi một event `answer_token` duy nhất chứa nguyên câu trả lời.

---

## 16. `clarification` — ClarificationAgent

**File:** [agents/clarification_agent.py](../agents/clarification_agent.py)

| Mục | Nội dung |
|---|---|
| **Đọc** | `clarification_question` (do `intent_agent` sinh) |
| **Ghi** | `answer`, `answer_format = "text"` |
| **Node tiếp theo** | `END` |

Không gọi LLM — chỉ lấy câu hỏi làm rõ mà `intent_agent` đã sinh sẵn, hoặc dùng `_DEFAULT_CLARIFICATION` nếu rỗng.

```python
{
  "answer": "Bạn muốn xem dữ liệu về sinh viên, điểm số hay học phí? Và trong khoảng thời gian nào?",
  "answer_format": "text"
}
```

---

## 17. Đầu ra cuối cùng về client

**File:** [api/routers/chat.py](../api/routers/chat.py) — sau khi `astream` kết thúc.

```json
{
  "event": "final_result",
  "data": {
    "answer": "Toàn trường hiện có 8.897 sinh viên đang học, phân bố ở 5 khoa...",
    "answer_format": "chart+text",
    "sql": "SELECT k.ten_khoa, COUNT(sv.ma_sv) AS so_luong_sinh_vien\nFROM sinh_vien sv\nJOIN khoa k ON sv.ma_khoa = k.ma_khoa\nWHERE sv.trang_thai = 'Đang học'\nGROUP BY k.ten_khoa\nORDER BY so_luong_sinh_vien DESC",
    "data": [
      {"ten_khoa": "Công nghệ thông tin", "so_luong_sinh_vien": 3421},
      {"ten_khoa": "Điện tử viễn thông", "so_luong_sinh_vien": 2187},
      {"ten_khoa": "Quản trị kinh doanh", "so_luong_sinh_vien": 1654},
      {"ten_khoa": "An toàn thông tin", "so_luong_sinh_vien": 892},
      {"ten_khoa": "Kế toán", "so_luong_sinh_vien": 743}
    ],
    "chart_config": {
      "chart_type": "bar",
      "x_axis": "ten_khoa",
      "y_axis": "so_luong_sinh_vien",
      "group_by": null,
      "title": "Số lượng sinh viên theo khoa",
      "x_label": "Khoa",
      "y_label": "Số sinh viên"
    },
    "execution_time_ms": 84.31,
    "total_execution_time": 7213.55,
    "node_execution_times": {
      "faq": 412.3, "domain_router": 634.1, "intent": 588.7,
      "schema": 1042.8, "knowledge": 431.2, "retrieval_join": 1.4,
      "sql_plan": 1876.5, "sql_gen": 1204.9, "sql_check": 152.6,
      "execute": 87.0, "data_check": 0.8, "chart": 943.2, "answer": 838.1
    },
    "slowest_node": "sql_plan",
    "intent": "chart_request",
    "error": null,
    "recommend_questions": [
      "Tỷ lệ sinh viên nam/nữ theo từng khoa?",
      "Số sinh viên nhập học mới năm 2026 theo khoa?",
      "Khoa nào có tỷ lệ sinh viên thôi học cao nhất?"
    ]
  }
}
```

Sau đó router ghi `Message(role="assistant")` vào DB nội bộ kèm metadata (`total_time`, `slowest_node`, `streaming`), và đẩy bản ghi lên Google Sheet.

---

## 18. Bảng tra nhanh — dữ liệu mỗi node

| Node | Đọc | Ghi | Gọi LLM? | Đi tiếp |
|---|---|---|---|---|
| `faq` | `user_query` | `intent`, `answer`, `recommend_questions` | Không (chỉ embed) | `answer` \| `domain_router` |
| `domain_router` | `user_query`, `domain`, `history` | `domain`, `domain_reasoning` | Có (chỉ khi `/chat` chung) | `intent` |
| `intent` | `user_query`, `history` | `intent`, `clarification_question` | **Có** | 5 nhánh |
| `schema` | `domain`, `user_query`, `selected_tables` | `relevant_tables`, `schema_context` | Chỉ khi fallback | `retrieval_join` |
| `knowledge` | `user_query`, `intent` | `knowledge_context`, `business_context` | Chỉ khi `knowledge_query` | `retrieval_join` |
| `retrieval_join` | — | — | Không | `answer` \| `sql_plan` |
| `sql_plan` | `schema_context`, `business_context`, `history` | `query_plan` | **Có** | `sql_gen` |
| `sql_gen` | `query_plan`, `schema_context`, các `issues` | `generated_sql`, `sql_reasoning` | **Có** | `sql_check` |
| `sql_check` | `generated_sql`, `schema_context` | `sql_correction`, `final_sql` | Chỉ khi EXPLAIN lỗi | `execute` \| `inc_retry` |
| `inc_retry` | `retry_count` | `retry_count` | Không | `sql_gen` |
| `execute` | `final_sql`, `domain` | `query_result`, `row_count`, `executor_error` | Không | `data_check` |
| `data_check` | `query_result`, `row_count`, `executor_error` | `data_check_is_valid`, `data_check_issues` | Không | `chart` \| `inc_data_retry` |
| `inc_data_retry` | `data_retry_count` | `data_retry_count` | Không | `sql_gen` |
| `chart` | `user_query`, `query_result` | `chart_config`, `chart_data`, `column_profiles` | **Có** | `answer` |
| `answer` | gần như toàn bộ state | `answer`, `answer_format` | Có (trừ 4 nhánh soạn sẵn) | `END` |
| `clarification` | `clarification_question` | `answer`, `answer_format` | Không | `END` |

### Số lượt gọi LLM cho một `chart_request` chạy trơn tru
`intent` (1) + `sql_plan` (1) + `sql_gen` (1) + `chart` (1) + `answer` (1) = **5 lượt**, cộng `domain_router` (1) nếu đi qua `/chat` chung → **6**. Mỗi vòng retry cộng thêm 1–2 lượt.

### Trần vòng lặp
- `sql_check` → `sql_gen`: tối đa **3** vòng.
- `data_check` → `sql_gen`: tối đa **1** vòng.
- `recursion_limit = 50` đặt ở router, dư so với đường đi xấu nhất (~24 super-step).
