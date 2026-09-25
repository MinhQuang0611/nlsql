## Báo cáo tối ưu hiệu năng hệ thống nlsql

### 1. Mục tiêu

- **Giảm độ trễ (latency)** cho mỗi request `/api/v1/chat` / `/api/v1/chat_with_table` / `/api/v1/chat_to_chart`.
- **Giữ nguyên độ chính xác** (hoặc tốt hơn), không hy sinh chất lượng câu trả lời.
- **Giảm chi phí LLM** (số lần gọi model / embedding).

---

### 2. Tổng quan luồng hiện tại (tóm tắt)

1. Client (web hoặc hệ thống khác) gọi API:
   - `/api/v1/chat` hoặc `/api/v1/chat_with_table`
2. Router dựng `initial_state` rồi chạy LangGraph:
   - `intent -> schema -> sql_plan -> sql_gen -> sql_check (retry) -> execute -> chart -> answer`
3. Một request full pipeline có thể gọi:
   - `intent_agent` (LLM)
   - `schema_agent` (Embeddings + Qdrant + DB)
   - `sql_plan_agent` (LLM)
   - `sql_gen_agent` (LLM + Embeddings + Qdrant few-shot)
   - `sql_check_agent` (EXPLAIN DB + LLM correction nếu lỗi)
   - `executor_agent` (DB + Redis)
   - `chart_agent` (LLM + profiling)
   - `answer_agent` (LLM)
   - `recommend.generate_recommend_questions` (LLM)

=> **6–8 lần LLM + 2 lần embeddings + nhiều round-trip DB** cho mỗi câu hỏi “đầy đủ”.

---

### 3. Các rủi ro chính gây chậm / không ổn định

#### 3.1. Số lần gọi LLM quá nhiều trên 1 request

- `intent`, `sql_plan`, `sql_gen`, `sql_check` (correction), `chart`, `answer`, `recommend` đều dùng LLM.
- Trong trường hợp SQL sai vài lần, `sql_check` có thể kích hoạt vòng lặp `sql_gen` → `sql_check` tối đa 3 lần.
- Đây là nguồn latency chính, đặc biệt nếu dùng model nặng (`gpt-4o`, `gpt-4o-mini`) qua network.

#### 3.2. Embedding lặp lại mà không cache

- `schema_agent` dùng `OpenAIEmbeddings.embed_query(user_query)` để query `schema_collection`.
- `sql_gen_agent` lại embed cùng `user_query` để query `few_shot_collection`.
- Chưa có cơ chế cache vector theo `user_query`, dẫn đến 2 request embedding cho cùng câu hỏi.

#### 3.3. Mismatch payload Qdrant schema → dễ gây lỗi / retry

- `scripts/index_schema.py` index vào Qdrant với payload:
  - `{"table_name": ..., "embed_text": ...}`
- `agents/schema_agent.py` lại đọc `hit.payload["schema_json"]` và `json.loads(...)`.
- Nếu collection được tạo theo script hiện tại:
  - truy cập `schema_json` sẽ lỗi `KeyError` hoặc `TypeError`, rơi vào block `except`.
  - Hệ quả: `schema_context` có thể rỗng hoặc thiếu → `sql_plan`/`sql_gen`/`sql_check` khó làm đúng → nhiều vòng retry/correction → tăng latency và rủi ro sai.

#### 3.4. Chart agent profiling trên nhiều dòng

- `executor_agent` đảm bảo `LIMIT` tối đa `MAX_ROWS=1000`.
- `chart_agent` gọi `profile_columns(query_result)` trên **toàn bộ rows** và mọi cột:
  - đếm unique values, infer type, gán role.
- Việc này tốn CPU khi bảng rộng (nhiều cột) hoặc nhiều dòng.

#### 3.5. Extra DB work: EXPLAIN / EXPLAIN ANALYZE

- `sql_check_agent` luôn gọi `EXPLAIN {generated_sql}` để kiểm tra SQL.
- `executor_agent`:
  - nếu `elapsed_ms > 2000` và DB là Postgres, thêm 1 lần `EXPLAIN ANALYZE {final_sql}` cho log.
- Các EXPLAIN này có ích cho debug, nhưng trong production chúng làm tăng thời gian xử lý đáng kể.

#### 3.6. Redis cache key chưa phân biệt đủ context

- `executor_agent` cache chỉ theo `user_query`:
  - Key: `sha256(user_query)`.
- Với `/chat_with_table`, `selected_tables` ảnh hưởng đến SQL, nhưng không nằm trong cache key:
  - Có thể trả nhầm kết quả cũ của query khác `selected_tables`.
  - Về hiệu năng thì vẫn “nhanh”, nhưng về correctness là rủi ro.

---

### 4. Chiến lược tối ưu (theo mức ưu tiên)

#### 4.1. Ưu tiên 1 — Sửa Qdrant schema payload cho đúng

**Vấn đề:** `schema_agent` kỳ vọng có `schema_json` trong payload nhưng `index_schema.py` không ghi.

**Giải pháp:**
- Trong `scripts/index_schema.py`, khi build `payload`, thêm lại:
  - `schema_json = json.dumps(schema, default=str)`
- Khi đó:
  - `schema_agent` không còn lỗi khi đọc `hit.payload["schema_json"]`.
  - `schema_context` sẽ luôn có đầy đủ thông tin từ lúc semantic search, giảm việc gọi DB lặp và LLM fallback.

**Lợi ích:**
- Giảm nguy cơ exceptions / retry.
- Giảm số lần `_fetch_table_schema` bị gọi lặp cho cùng bảng.
- Cải thiện cả hiệu năng lẫn độ ổn định.

#### 4.2. Ưu tiên 2 — Giảm số lần gọi LLM trong pipeline

**A. Bỏ (hoặc điều kiện hóa) `sql_plan_agent`**

- Hiện tại:
  - `sql_plan_agent` tạo `query_plan` trung gian.
  - `sql_gen_agent` lại dùng `query_plan` + `schema_context` để sinh SQL.
- Trên thực tế, nhiều hệ thống Text-to-SQL vẫn đạt chất lượng tốt khi nhảy thẳng từ:
  - `user_query + schema_context + few-shot` → SQL, không cần bước “plan” riêng.

**Đề xuất:**
- Bước 1 (an toàn):
  - Cho phép tắt `sql_plan_agent` qua flag config (ví dụ `ENABLE_SQL_PLAN=false`) và:
    - Nếu tắt, builder bỏ node `sql_plan`; `schema` nối thẳng sang `sql_gen`.
    - `sql_gen_agent` xử lý khi `query_plan` = rỗng.
- Bước 2 (sau khi test):
  - Nếu chất lượng không giảm nhiều, có thể bỏ hẳn `sql_plan_agent` khỏi pipeline.

**B. Hạn chế gọi `chart_agent` khi không cần**

- Nếu client không hiển thị chart, có thể:
  - Cho phép client truyền cờ `want_chart: bool`.
  - Nếu `want_chart=false` → bỏ qua node `chart` (builder nối `execute` → `answer`).

**C. Tùy chọn tắt `recommend_questions`**

- `generate_recommend_questions` gọi LLM riêng.
- Cho phép cấu hình:
  - Mặc định trong prod: `num_recommend=0` để tắt recommend từ server.
  - Khi cần demo/POC có thể bật lại.

#### 4.3. Ưu tiên 3 — Cache embedding cho `user_query`

**Hiện trạng:**
- `schema_agent` và `sql_gen_agent` đều embedding `user_query` (2 lần).

**Đề xuất:**
- Tạo một layer cache:
  - Có thể dùng LRU trong memory (process-local) hoặc Redis:
    - Key: `emb:{model}:{user_query_hash}`
    - Value: vector embedding.
- Ở `schema_agent` và `sql_gen_agent`:
  - Thử lấy từ cache trước, chỉ gọi `OpenAIEmbeddings.embed_query(...)` khi miss.

**Lợi ích:**
- Tiết kiệm 1 lần embedding / request (hoặc hơn, nếu sau này còn chỗ dùng).
- Rất hiệu quả với câu hỏi lặp lại hoặc khi user “chỉnh sửa nhẹ” câu hỏi.

#### 4.4. Ưu tiên 4 — Tối ưu chart profiling + chart selection

**A. Profile trên sample thay vì full 1000 dòng**

- Thay vì dùng toàn bộ `query_result` trong `profile_columns`:
  - chỉ dùng `query_result[:N]` với `N` nhỏ (ví dụ 200).
- Với `n_unique`:
  - có thể cắt ngưỡng: nếu đã thấy > 100 giá trị khác nhau thì dừng (đánh dấu là “high cardinality”).

**B. Dùng heuristic để chọn chart_type trước, LLM chỉ fallback**

- Dựa trên:
  - số cột numeric vs categorical
  - số hàng
  - có cột ngày/tháng hay không (dùng `ColumnProfile.inferred_type == "date"`)
- Áp dụng gần giống rule trong prompt `CHART_SYSTEM`:
  - 1 dòng 1 cột số → `number`
  - có cột date + 1 cột số → `line`
  - ít nhóm + 1 cột số → `bar` hoặc `pie`
  - 2 cột số → `scatter`
  - còn lại → `table`
- Chỉ khi dữ liệu phức tạp / ambiguous mới gọi `chart_agent` (LLM) để refine.

**Lợi ích:**
- Giảm số câu hỏi chart gửi tới LLM.
- Giảm CPU profiling nếu UE không thực sự cần chart cao cấp.

#### 4.5. Ưu tiên 5 — Giảm EXPLAIN/ANALYZE trong môi trường production

**Đề xuất:**

- `sql_check_agent`:
  - Cho phép tắt `EXPLAIN` trong production (chỉ rely vào LLM correction hoặc check đơn giản hơn).
  - Hoặc:
    - EXPLAIN chỉ với query “nguy hiểm” (ví dụ nhiều join, không có limit).

- `executor_agent`:
  - `EXPLAIN ANALYZE` chỉ nên bật khi:
    - `app_env == "development"`, hoặc
    - có cờ debug bật tạm thời.

**Lợi ích:**
- Giảm đáng kể thời gian xử lý cho các query phức tạp/số dòng lớn trong production.

#### 4.6. Ưu tiên 6 — Cải thiện Redis cache key

**Đề xuất:**

- Thay vì chỉ hash `user_query`, consider:
  - Kết hợp thêm `sorted(selected_tables)` (nếu có).
  - Option nâng cao:
    - Cache theo `final_sql` thay vì `user_query` (tức là caching sau khi SQL đã sinh xong).

**Lợi ích:**
- Tránh trả nhầm kết quả cho các context khác nhau.
- Cho phép tái dùng cache khi nhiều user hỏi giống nhau, bất kể `user_query` wording có khác đôi chút, miễn `final_sql` giống nhau (trường hợp cache theo SQL).

---

### 5. Ước lượng tác động (định tính)

- **Sửa Qdrant payload + giảm LLM (bỏ sql_plan / limit chart agent):**
  - Giảm 1–2 lần LLM + giảm retry do schema lỗi.
  - Với model remote, mỗi lần LLM có thể chiếm vài trăm ms đến vài giây → giảm đáng kể p95 latency.

- **Cache embeddings:**
  - Mỗi embedding call thường vài trăm ms.
  - Cache giúp tiết kiệm ~1 call / request.

- **Giảm EXPLAIN/ANALYZE trong sản xuất:**
  - Với query phức tạp, EXPLAIN ANALYZE có thể gấp 2–3 lần thời gian SELECT thường.

- **Chart heuristic + sample profiling:**
  - Ít ảnh hưởng độ chính xác nhưng giảm CPU + LLM call, đặc biệt khi data rộng.

---

### 6. Kết luận & khuyến nghị triển khai

- **Bước 1 (ngay lập tức):**
  - Bật `schema_json` trong `scripts/index_schema.py`.
  - Thêm config để tắt `EXPLAIN ANALYZE` trong `executor_agent` khi `app_env="production"`.

- **Bước 2 (ngắn hạn):**
  - Thêm flag cho phép bỏ qua `sql_plan_agent` và `recommend_questions` trong môi trường production.
  - Triển khai cache embedding (`user_query` → vector) dùng LRU/Redis.

- **Bước 3 (trung hạn):**
  - Refactor `chart_agent` để:
    - profile trên sample.
    - dùng heuristic chọn chart_type trước, LLM chỉ refine khi cần.

- **Bước 4 (dài hạn):**
  - Đo đạc bằng metrics (log thời gian từng node trong graph):
    - log thời gian `intent`, `schema`, `sql_gen`, `sql_check`, `execute`, `chart`, `answer`.
  - Dựa vào số liệu thực tế để tinh chỉnh thêm (ví dụ: thay model nhẹ hơn cho `intent`/`recommend`, hoặc gộp một số bước LLM lại).

