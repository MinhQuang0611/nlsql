# nlsql — Luồng chạy chi tiết (end-to-end)

Tài liệu này giải thích luồng thực thi của dự án `nlsql` theo đúng code hiện có trong thư mục `/home/ubuntu/Desktop/quangnm/nlsql`.

## 1) Thành phần chính trong hệ thống

1. Web server: `FastAPI` chạy bằng `uvicorn` (`main.py`, `entrypoint.sh`).
2. Orchestration (luồng đa agent): `LangGraph StateGraph` (`graph/builder.py`, `graph/state.py`).
3. Các “agent” (node trong graph):
   - `intent_agent` (`agents/intent_agent.py`)
   - `schema_agent` (`agents/schema_agent.py`)
   - `sql_plan_agent` (`agents/sql_plan_agent.py`)
   - `sql_gen_agent` (`agents/sql_gen_agent.py`)
   - `sql_check_agent` (`agents/sql_check_agent.py`)
   - `executor_agent` (`agents/executor_agent.py`)
   - `chart_agent` (`agents/chart_agent.py`)
   - `answer_agent` (`agents/answer_agent.py`)
   - `clarification_agent` (`agents/clarification_agent.py`)
4. Prompt (hệ thống + câu hỏi người dùng) cho từng agent: `prompts/*`.
5. Database schema retrieval:
   - Vector search Schema: `Qdrant` (`scripts/index_schema.py` + `schema_agent`)
   - Few-shot SQL: `Qdrant` (`scripts/index_few_shot.py` + `sql_gen_agent`)
6. Query execution:
   - `Postgres` (AsyncSQLAlchemy/asyncpg) hoặc `ClickHouse` tùy `active_db` (`config.py`, `db/connection.py`)
7. Cache + giới hạn truy vấn:
   - `Redis` caching result theo `user_query` hash (`agents/executor_agent.py`)
8. UI tĩnh (demo):
   - `static/chat.html` gọi API backend (`/api/v1/tables`, `/api/v1/chat`, `/api/v1/chat_with_table`, `/api/v1/chart`, `/api/v1/chat_to_chart`).

## 2) Startup / Khởi động server

### 2.1. Docker entrypoint

`entrypoint.sh`:
1. Nếu `DB_HOST` và `DB_PORT` có giá trị, script sẽ “wait” đến khi cổng DB mở (dùng `/dev/tcp`).
2. Nếu `APP_ENV=development`:
   - chạy `uvicorn main:app --host 0.0.0.0 --port 8388 --reload`
3. Ngược lại:
   - chạy `uvicorn main:app --host 0.0.0.0 --port 8388 --workers 2`

> Lưu ý: trong `Dockerfile` có `EXPOSE 8386` nhưng entrypoint lại chạy `8388` (không ảnh hưởng nếu compose mapping đúng, nhưng là chênh lệch cần để ý).

### 2.2. FastAPI lifespan (khởi động ứng dụng)

Trong `main.py`, `lifespan(app)` làm các bước:
1. Log: “Starting nlsql [env=...]”
2. Gọi `check_db_connection()` (`db/connection.py`)
   - Postgres: `SELECT version()`
   - ClickHouse: `_ch_execute("SELECT version()")`
   - Nếu status != `"ok"` => raise `RuntimeError` để fail startup.
3. Nếu `settings.app_env == "development"`:
   - gọi `init_db()` để tạo schema ORM (chỉ áp dụng Postgres).
4. “Checking/indexing schema...”:
   - gọi `scripts/index_schema.main()` (để populate `schema_collection` vào Qdrant).
5. `yield` => server sẵn sàng.
6. Khi shutdown:
   - gọi `close_db()` (dispose engine/connect).

### 2.3. Cấu hình app & route

`main.py` tạo `app = create_app()`:
1. CORS cho `allow_origins=["*"]`.
2. Include routers với prefix `/api/v1`:
   - `api.routers.chat.router` (chat endpoint)
   - `api.routers.tables.router` (list tables)
   - `api.routers.chart.router` (chart endpoint)
3. Mount `/static` từ thư mục `static/`.
4. Route:
   - `GET /chat` trả về file `static/chat.html`
   - `GET /` trả JSON {service, version, status}
   - `GET /health` trả tình trạng DB (HTTP 200 nếu ok, 503 nếu lỗi)

## 3) Dữ liệu điều khiển luồng: AgentState

`graph/state.py` định nghĩa `AgentState` (TypedDict). Các key quan trọng:

1. Input:
   - `user_query`: câu hỏi thô người dùng
   - `session_id`: id phiên chat (chỉ phục vụ log/history)
   - `selected_tables` (optional): giới hạn bảng (dùng ở endpoint `/chat_with_table`)
   - `retry_count`: số lần retry vòng sql_gen/sql_check
   - `history`: history chat (được lưu ở router, không nằm trong state typed dict)
   - `num_recommend` (optional): số câu gợi ý follow-up
2. Intent & schema:
   - `intent`, `intent_reasoning`, `clarification_question`
   - `relevant_tables`
   - `schema_context`, `pruned_schema_context` (code hiện tại dùng `schema_context`, chưa thấy dùng `pruned_schema_context`)
3. SQL:
   - `query_plan`
   - `generated_sql`, `sql_reasoning`
   - `sql_correction` (cờ hợp lệ + issues + fixed_sql)
   - `final_sql`
4. Execution:
   - `query_result`: list[dict]
   - `row_count`
   - `execution_time_ms`
   - `executor_error`
5. Chart:
   - `forced_chart_type` (optional)
   - `column_profiles`
   - `chart_config`
   - `chart_data`
6. Output:
   - `answer`
   - `answer_format`: `text` | `table` | `chart+text`
   - `error` (trong code trả lỗi qua exception hoặc qua `executor_error`)

## 4) Route vào pipeline LangGraph (API layer)

### 4.1. Endpoint `/api/v1/chat`

File: `api/routers/chat.py`

Khi `POST /api/v1/chat`:
1. Nhận `ChatRequest`:
   - `query`, `session_id`, `history`, `num_recommend`
2. Tạo `initial_state`:
   - `user_query = request.query`
   - `session_id = request.session_id`
   - `retry_count = 0`
   - `history = [m.model_dump() ...]` (đưa xuống để dùng cho recommend questions)
   - `num_recommend = request.num_recommend`
3. Gọi `_process_chat(initial_state)`

`_process_chat`:
1. Lấy `num_recommend` và `history` ra khỏi state (pop).
2. Copy `final_state = initial_state.copy()`.
3. Chạy graph: `async for output in graph_app.astream(initial_state):`
   - `output` là map `node_name -> state_update` (mỗi bước agent trả một phần state cập nhật).
   - Router log từng node hoàn tất và merge `final_state.update(state_update)`.
4. Sau khi graph END:
   - gọi `utils.recommend.generate_recommend_questions(...)` nếu `num_recommend > 0`
   - dựng `ChatResponse`:
     - `answer = final_state["answer"]` (fallback lỗi)
     - `answer_format = final_state["answer_format"]`
     - `sql = final_state["final_sql"]` (được trả về; UI có chỗ hiển thị)
     - `data = final_state["query_result"]`
     - `chart_config`, `execution_time_ms`, `intent`, `executor_error`
     - `recommend_questions`
5. Nếu `settings.google_sheet_url` tồn tại:
   - append log bất đồng bộ sang Google Sheet (không chặn request).
6. Trả response.

### 4.2. Endpoint `/api/v1/chat_with_table`

Cũng như `/chat`, nhưng nhận thêm:
- `selected_tables` (list[str])

`initial_state` thêm:
- `selected_tables = request.selected_tables`

Điểm khác: node `schema_agent` sẽ ưu tiên lấy schema theo `selected_tables` nếu present.

### 4.3. Endpoint `/api/v1/tables` (UI dùng để chọn bảng)

File: `api/routers/tables.py`

`GET /api/v1/tables`:
1. Gọi `_fetch_all_tables()` từ `agents/schema_agent.py`
2. Load Excel mapping `QLDT_FINAL.xlsx` sheet `Database Schema`:
   - mapping từ “Tên bảng” -> “Tên tiếng Việt” cho các dòng header.
3. Trả dict `{table_name: excel_vi_name_or_empty}`

> Nếu file Excel không tồn tại hoặc đường dẫn không đúng, endpoint vẫn trả map (nhưng mô tả bảng sẽ trống).

### 4.4. Các endpoint chart riêng

File: `api/routers/chart.py`

1. `POST /api/v1/chart`:
   - Nhận `ChartRequest(user_query, data, chart_type?)`
   - Gọi `run_chart_agent(...)` trực tiếp (không chạy intent/sql/executor).
2. `POST /api/v1/chat_to_chart`:
   - Nhận `ChatToChartRequest(query, session_id, chart_type?)`
   - Gọi toàn pipeline graph giống `/chat`, nhưng:
     - initial_state không có `history`
     - chỉ thêm `forced_chart_type` nếu user chỉ định `chart_type`.

## 5) LangGraph pipeline: các node và điều kiện chuyển tiếp

File: `graph/builder.py`

Graph nodes:
1. `intent` -> `intent_agent`
2. `schema` -> `schema_agent`
3. `sql_plan` -> `sql_plan_agent`
4. `sql_gen` -> `sql_gen_agent`
5. `sql_check` -> `sql_check_agent`
6. `inc_retry` -> tăng `retry_count`
7. `execute` -> `executor_agent`
8. `chart` -> `chart_agent`
9. `answer` -> `answer_agent`
10. `clarification` -> `clarification_agent`

Các edge:
1. START -> `intent`
2. `intent` (conditional):
   - nếu intent in (`data_query`, `chart_request`, `schema_question`) => `schema`
   - nếu `ambiguous` => `clarification`
   - nếu khác (greeting, out_of_scope) => `answer`
3. `schema` (conditional):
   - nếu intent == `schema_question` => `answer`
   - else => `sql_plan`
4. `sql_plan` -> `sql_gen` -> `sql_check`
5. `sql_check` (conditional, vòng retry):
   - nếu `sql_correction.is_valid == True` => `execute`
   - else:
     - nếu `retry_count >= 3`: log warning và vẫn `execute` (dù fixed_sql có thể rỗng)
     - ngược lại: `sql_gen` thông qua `inc_retry`
6. `execute` -> `chart` -> `answer` -> END
7. `clarification` -> END (không chạy schema/sql)

## 6) Chi tiết từng agent (node)

### 6.1. `intent_agent` — phân loại ý định

File: `agents/intent_agent.py`

1. Lấy `user_query` từ state.
2. Tạo `messages`:
   - `SystemMessage(INTENT_SYSTEM)`
   - `HumanMessage(INTENT_HUMAN.format(user_query=user_query))`
3. Dùng `ChatOpenAI(..., temperature=0)` với `with_structured_output(IntentClassifierSchema)`
4. Lấy kết quả:
   - `intent`, `reasoning`, `clarification_question`
5. Nếu intent trả về không nằm trong `VALID_INTENTS`:
   - fallback `intent = "out_of_scope"`
6. Return state update:
   - `intent`
   - `intent_reasoning`
   - `clarification_question`

### 6.2. `schema_agent` — chọn bảng & trích schema ngữ cảnh

File: `agents/schema_agent.py`

Mục tiêu: tạo `schema_context` cho các agent SQL sau đó, bằng cách:
- nếu có `selected_tables` => lấy trực tiếp
- nếu không => dùng semantic search Qdrant để lấy bảng liên quan

Trường hợp A: có `selected_tables`
1. Log: giới hạn truy vấn
2. Loop theo bảng:
   - gọi `_fetch_table_schema(t)` cho từng bảng
3. Return update:
   - `relevant_tables = selected_tables`
   - `schema_context = schema_context_list`

Trường hợp B: không có `selected_tables`
1. Thiết lập:
   - `SCORE_THRESHOLD = 0.68`
   - `SEARCH_LIMIT = 20`
2. Qdrant semantic search:
   - Embedding query từ `user_query`
   - Query vào collection `schema_collection` với `with_payload=True`
3. Dedup:
   - “giữ điểm cao nhất” theo `table_name` trong payload
4. Lọc bảng:
   - chọn các bảng có `hit.score >= SCORE_THRESHOLD`
5. Với mỗi bảng passed:
   - lấy `hit.payload["schema_json"]` rồi `json.loads(...)`
   - append vào `schema_context`
6. Fallback LLM khi ít bảng (<2):
   - lấy danh sách tất cả bảng bằng `_fetch_all_tables()`
   - prompt LLM liệt kê bảng có thể liên quan (chỉ trả tên bảng, mỗi dòng một bảng)
   - lọc các tên bảng hợp lệ và fetch schema từng bảng

Return update:
- `relevant_tables`
- `schema_context`

#### Điểm chú ý / bug quan trọng (schema_json mismatch)

Trong `scripts/index_schema.py`, payload upsert vào Qdrant hiện tại chỉ chứa:
- `table_name`
- `embed_text`

Trong khi `schema_agent` lại đọc:
- `hit.payload["schema_json"]`

`schema_json` đang bị comment out ở `scripts/index_schema.py`:
- dòng `"schema_json": json.dumps(schema, ...)` bị tắt.

Hệ quả: nếu `schema_collection` đúng theo code index hiện tại, bước schema semantic search trong `schema_agent` sẽ ném lỗi `KeyError: 'schema_json'` và có thể làm pipeline fail (do exception nằm trong block try chung của Qdrant search).

### 6.3. `sql_plan_agent` — lập kế hoạch reasoning SQL

File: `agents/sql_plan_agent.py`

1. Lấy `user_query`, `schema_context`.
2. Nếu `schema_context` rỗng:
   - return `query_plan = "No schema information provided."`
3. `_format_schema_context(schema_context)`:
   - render mỗi bảng dạng:
     - tên bảng
     - description (nếu có)
     - list cột (name + type + NULL/NOT NULL + comment/excel fields)
     - foreign keys (nếu có)
     - sample row (nếu có)
   - còn nhúng thêm rule `settings.TABLE_RULES[table]` nếu bảng có quy tắc.
4. Gọi LLM:
   - `SystemMessage(SQL_PLAN_SYSTEM)`
   - `HumanMessage(SQL_PLAN_HUMAN.format(user_query=..., schema_context=...))`
5. Lấy `response.content` => `query_plan`

Return update:
- `query_plan`

### 6.4. `sql_gen_agent` — sinh câu SQL từ plan + schema (+ few-shot)

File: `agents/sql_gen_agent.py`

Inputs từ state:
- `user_query`
- `schema_context`
- `query_plan`
- `retry_count`

Các bước:
1. Render `schema_context` vào string `_format_schema_context`.
2. Nếu `retry_count > 0`:
   - lấy `state["sql_correction"]["issues"]`
   - nhúng vào `SQL_GEN_RETRY_HINT` để model tránh các lỗi cũ.
3. Few-shot retrieval (tùy cấu hình Qdrant + key):
   - Query `few_shot_collection` với embedding của `user_query`
   - ghép chuỗi few-shot dạng:
     - `Q: ...\nSQL: ...`
4. Gọi LLM dạng structured output với schema:
   - `SQLGenerationSchema(sql, reasoning)`
5. Lấy:
   - `generated_sql = response.sql.strip()`
   - `sql_reasoning = response.reasoning`
6. Reset correction state:
   - `sql_correction = {"is_valid": False, "issues": [], "fixed_sql": None}`
   - `final_sql = ""`

Return update:
- `generated_sql`
- `sql_reasoning`
- `sql_correction` (reset)
- `final_sql` (xóa)

### 6.5. `sql_check_agent` — “dry run” bằng EXPLAIN và sửa lỗi bằng LLM nếu cần

File: `agents/sql_check_agent.py`

Bước safety cứng:
1. `_hard_safety_check(generated_sql)`:
   - dùng regex chặn các keyword nguy hiểm: `INSERT|UPDATE|DELETE|DROP|...`
2. Nếu phát hiện keyword nguy hiểm:
   - return `sql_correction.is_valid = False`
   - `fixed_sql=None`
   - đồng thời `final_sql=""`

Bước kiểm tra “chạy được”:
3. Thử chạy `EXPLAIN {generated_sql}`
   - Postgres: `engine.connect().execute(text(f"EXPLAIN ..."))`
   - ClickHouse: `ch_execute(f"EXPLAIN {generated_sql}")`
4. Nếu `EXPLAIN` pass:
   - set `sql_correction.is_valid=True`
   - `final_sql = generated_sql`
5. Nếu `EXPLAIN` fail:
   - lấy `db_error_msg`
   - gọi LLM sửa câu SQL:
     - `SQL_CORRECTION_SYSTEM`
     - `SQL_CORRECTION_HUMAN` nhúng:
       - `invalid_sql`
       - `error_message`
       - `schema_summary` (từ `_format_schema_summary(schema_context)`)
   - LLM trả structured output `SQLCorrectionSchema(is_valid, issues, fixed_sql)`
   - nếu có `fixed_sql`:
     - `_hard_safety_check` lần nữa; nếu pass => return.

Return update:
- `sql_correction`
- `final_sql` (có thể rỗng nếu LLM không trả fixed_sql)

### 6.6. `executor_agent` — thực thi SQL trên DB, cache kết quả, giới hạn số dòng

File: `agents/executor_agent.py`

Inputs:
- `final_sql`
- `user_query`

Trình tự:
1. Nếu `final_sql` rỗng:
   - return với `executor_error = "No valid SQL to execute."`
2. Chặn SQL nguy hiểm trong môi trường không phải development:
   - nếu `settings.app_env != "development"` và SQL chứa keyword nguy hiểm:
     - return `executor_error` dạng security blocked

3. Redis cache:
   - tạo `query_hash = sha256(user_query)`
   - cache key: `nlsql:query:{query_hash}`
   - nếu cache hit:
     - trả thẳng `query_result`, `row_count`
     - set `execution_time_ms=0.0`
     - `executor_error=None`

4. Chuẩn hóa LIMIT:
   - xóa `;` cuối câu
   - nếu không có từ `LIMIT` (case-insensitive):
     - ClickHouse: thêm `\nLIMIT {MAX_ROWS}`
     - Postgres: bọc subquery: `SELECT * FROM ({clean_sql}) AS _subquery LIMIT {MAX_ROWS}`
   - `MAX_ROWS = 1000`

5. Execute:
   - ClickHouse: `ch_execute(sql)` rồi chuyển row->dict (có các nhánh kiểu row mapping)
   - Postgres: `get_db_context()` execute text(sql), lấy keys + fetchmany(MAX_ROWS)
6. Sau execute:
   - set `row_count = len(rows)`
   - log slow queries:
     - nếu `elapsed_ms > 2000` và active_db != clickhouse:
       - chạy `EXPLAIN ANALYZE {final_sql}` và log output
   - cache result vào Redis trong 3600s (nếu cache_key tồn tại)

Return update:
- `query_result`
- `row_count`
- `execution_time_ms`
- `executor_error=None` hoặc error message

#### Điểm chú ý / rủi ro cache key

Cache key hiện chỉ dựa vào `user_query`. Nếu client dùng endpoint `/chat_with_table` và truyền `selected_tables`, nhưng `executor_agent` không đưa `selected_tables` vào cache key => có thể trả kết quả sai cho cùng `user_query` nhưng khác filter schema.

### 6.7. `chart_agent` — chọn chart_type và reshape data

File: `agents/chart_agent.py`

Inputs:
- `query_result`: list[dict] từ DB
- `user_query`
- `forced_chart_type` (optional)

Bước:
1. Nếu `query_result` rỗng:
   - default chart_type = `table`
2. Validate `forced_chart_type` có nằm trong `VALID_CHART_TYPES`.
3. Column profiling:
   - `profiles = profile_columns(query_result)` (`utils/data_profiler.py`)
   - `column_profile_text = format_profile_for_prompt(profiles)`
4. Lấy:
   - `columns = list(query_result[0].keys())`
   - `sample_rows = query_result[:3]`
5. Build prompt:
   - Nếu có forced_chart_type:
     - dùng `CHART_HUMAN_FORCED` bắt buộc output chart_type=forced_chart_type
   - else:
     - dùng `CHART_HUMAN`
   - System: `CHART_SYSTEM`
6. Parse output JSON:
   - `_parse_llm_response(raw, user_query)`:
     - `json.loads(raw)`
     - check `chart_type` trong set hợp lệ
     - nếu parse lỗi => fallback chart_type=`table`
7. Reshape dữ liệu:
   - `_reshape_for_chart(rows, chart_config)`:
     - chart_type=`number`: trả `rows[:1]`
     - chart_type khác:
       - tạo mỗi point gồm `x`, `y`, `group` (nếu config tương ứng có cột trong row)
       - giữ các cột còn lại trong point
8. Điều chỉnh hậu xử lý:
   - `adjust_chart_data(chart_data, chart_config, profiles)`:
     - sort desc theo y cho `bar/pie`
     - gán x_label/y_label nếu LLM để null
     - gộp nhóm nhỏ dưới ngưỡng `other_threshold_pct` (mặc định 2%) vào `Khác`

Return update:
- `chart_config`
- `chart_data`
- `column_profiles`

### 6.8. `answer_agent` — viết câu trả lời cuối

File: `agents/answer_agent.py`

Nhận:
- `user_query`
- `query_result`, `row_count`
- `chart_config`
- `intent`
- `executor_error`

Xử lý các intent đặc biệt:
1. `out_of_scope` => xin lỗi, chỉ trả lời câu hỏi liên quan DB.
2. `greeting` => chào + hỏi nhu cầu.
3. `schema_question` => trả lời “Database có các bảng liên quan: ...”
4. `executor_error` => trả lời lỗi thực thi.

Với intent dữ liệu bình thường:
5. Preview rows: `query_result[:10]`
6. `has_chart = chart_config is not None`
7. Gọi LLM:
   - System: `ANSWER_SYSTEM`
   - Human: `ANSWER_HUMAN.format(user_query, row_count, query_result=preview_rows, has_chart)`
8. Parse output JSON:
   - `answer = parsed["answer"]`
   - `answer_format = parsed.get("answer_format", "text")`
   - validate `answer_format` trong `{"text","table","chart+text"}`
   - nếu LLM trả sai/parse lỗi => fallback `answer_format` theo `has_chart`

Return update:
- `answer`
- `answer_format`

### 6.9. `clarification_agent` — hỏi lại khi intent mơ hồ

File: `agents/clarification_agent.py`

1. Lấy `clarification_question` từ state
2. Nếu không có:
   - dùng `_DEFAULT_CLARIFICATION`
3. Return:
   - `answer = clarification_question`
   - `answer_format="text"`

## 7) Luồng hoàn chỉnh theo kịch bản request

### 7.1. User gọi `POST /api/v1/chat`

1. Router build `initial_state` gồm:
   - `user_query`, `session_id`, `retry_count=0`, `history=[...]`, `num_recommend`
2. Graph START:
   - Node `intent`:
     - phân loại intent
     - nếu `ambiguous` => trả ngay clarification và END
     - nếu `greeting/out_of_scope` => sang `answer` và END
     - nếu `data_query/chart_request/schema_question` => sang `schema`
3. Node `schema`:
   - nếu intent=`schema_question` => sang `answer` luôn
   - else:
     - lấy `relevant_tables` và `schema_context` (từ Qdrant hoặc selected_tables)
4. Node `sql_plan`:
   - sinh `query_plan` từ user_query + schema_context
5. Node `sql_gen`:
   - sinh `generated_sql` từ query_plan + schema_context (+ few-shot nếu có)
6. Node `sql_check`:
   - chặn SQL nguy hiểm
   - chạy `EXPLAIN`
   - nếu fail => LLM fix SQL (giữ `sql_correction.is_valid`)
7. Conditional retry:
   - nếu `sql_correction.is_valid=True` => `execute`
   - nếu invalid và retry_count<3 => `inc_retry` => quay lại `sql_gen`
   - nếu retry_count>=3 => vẫn `execute` (dù fixed_sql có thể rỗng)
8. Node `execute`:
   - chạy SQL (LIMIT tự động) + caching Redis
   - trả `query_result`, `row_count`, `execution_time_ms`
9. Node `chart`:
   - dùng chart prompt + column profiling + reshape + adjust
10. Node `answer`:
   - LLM viết câu trả lời cuối theo intent/data/chart
11. Router sau END:
   - sinh recommend questions từ (history + user_query + answer)
   - trả `ChatResponse`.

### 7.2. User gọi `POST /api/v1/chat_with_table`

Giống `/chat`, nhưng:
- state ban đầu thêm `selected_tables`
- node `schema_agent` sẽ fetch schema trực tiếp theo `selected_tables` thay vì Qdrant.

## 8) Qdrant: cách populate dữ liệu cho bước semantic search

### 8.1. Schema indexing (`scripts/index_schema.py`)

`main()` trong script:
1. Tạo/kiểm tra collection `schema_collection`:
   - nếu chưa tồn tại => create `vectors_config` (size=1536, cosine)
   - nếu tồn tại => “Recreate it” (code hiện tại thực tế chỉ `return` nếu đã tồn tại, tức là bỏ indexing nếu đã có collection; nhưng output error.log cho thấy phiên bản trước có delete/recreate).
2. Lấy danh sách bảng: `_fetch_all_tables()` (từ `agents/schema_agent.py`)
3. Load Excel metadata `QLDT_FINAL.xlsx`:
   - dùng `load_excel_metadata(file_path)` để map tên cột/cột tiếng Việt.
4. Loop từng bảng:
   - `schema = await _fetch_table_schema(table_name)`
   - trích `excel_table_desc` + cột tiếng Việt vào embed_text
   - tạo `embed_text` gồm:
     - sentence table description/purpose
     - sentence list columns
     - (optional) enum hints
     - (optional) foreign keys
   - embedding `vector = embeddings.embed_query(embed_text)`
   - upsert payload hiện tại:
     - `{"table_name": table_name, "embed_text": embed_text}`

### 8.2. Few-shot indexing (`scripts/index_few_shot.py`)

Script tạo collection `few_shot_collection` và upsert payload dạng:
- `question`
- `sql`

Nếu collection đã tồn tại: code hiện tại sẽ delete và recreate.

## 9) UI tĩnh (`static/chat.html`) kết nối backend như thế nào

`chat.html` (demo) làm:
1. Khi load:
   - gọi `GET /api/v1/tables` để render danh sách bảng + checkbox chọn `selectedTables`
2. Khi user gửi query:
   - nếu chọn bảng (`selectedTables.size > 0`):
     - POST `/api/v1/chat_with_table`
   - else:
     - POST `/api/v1/chat`
   - body có `history: chatHistory.slice(0, -1)` và `num_recommend: 3`
3. Khi nhận response:
   - hiển thị `answer`
   - nếu có `data` => hiển thị bảng dữ liệu (top 10 dòng)
   - nếu có `chart_config` + `chart_data` => render chart bằng Vega-Lite
   - có phần “switch chart type” bằng gọi lại `/api/v1/chat_to_chart` với `chart_type` do user chọn.

## 10) Các script / test trong repo (để hiểu cách vận hành)

1. `scripts/test_db_connection.py`:
   - ping DB + kiểm tra tồn tại dữ liệu seed tables.
2. `scripts/test_pg_schema.py`:
   - gọi `_fetch_all_tables()` và `_fetch_table_schema()` để in schema sample.
3. `scripts/test_asynch.py`:
   - thử import/monkeypatch cho `asynch` và tạo engine clickhouse (liên quan comment trong `db/connection.py`).
4. `test/debug_run.py`:
   - chạy graph local qua `app.ainvoke(state)` để in ra intent/query_plan/generated_sql/final_sql/answer.
5. `test/test_parallel.py` và `test/test_explain.py`:
   - các test mẫu cho LangGraph/ClickHouse explain (không dùng trong flow chính).

## 11) Những điểm cần chú ý / rủi ro từ code hiện tại

1. Bug payload Qdrant schema:
   - `scripts/index_schema.py` upsert payload thiếu `schema_json`
   - `agents/schema_agent.py` lại cố đọc `hit.payload["schema_json"]`
   - Khuyến nghị:
     - hoặc uncomment và upsert `schema_json`
     - hoặc sửa `schema_agent` để fetch schema theo `table_name` sau khi semantic search (không cần schema_json trong payload).
2. Redis cache key chỉ theo `user_query`:
   - có thể trả sai nếu endpoint `/chat_with_table` truyền `selected_tables` khác nhau cho cùng `user_query`.
3. Retry logic khi `retry_count >= 3`:
   - builder vẫn `execute` ngay cả khi `sql_correction.is_valid` false
   - nếu `final_sql` rỗng => executor trả `executor_error = "No valid SQL to execute."` và answer sẽ report lỗi.
4. `sql_check_agent` dùng `EXPLAIN {sql}`:
   - nếu LLM sinh SQL không tương thích một phần schema sẽ fail và phụ thuộc vào sửa lỗi bằng LLM.
5. Excel file `QLDT_FINAL.xlsx`:
   - cả `scripts/index_schema.py` và `api/routers/tables.py` đều cần file này theo đường dẫn tương đối.
6. Trường `active_db`:
   - config cho phép `postgres` hoặc `clickhouse`
   - trong clickhouse mode, engine ORM/postgres metadata không dùng; các phần check sql/execute đã có nhánh clickhouse.

## 12) Tóm tắt cực ngắn

Request `/api/v1/chat` đi qua graph:
`intent -> schema -> sql_plan -> sql_gen -> sql_check (retry) -> execute -> chart -> answer`,
trong đó `schema` và `sql_gen` dùng Qdrant, còn `execute` dùng DB + Redis cache.

