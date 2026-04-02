## Phân tích chi tiết 1 lần hỏi: “Thống kê sinh viên theo từng ngành học”

File này phân tích log bạn cung cấp cho một request `/api/v1/chat` với câu hỏi:

> **Thống kê sinh viên theo từng ngành học**

Mục tiêu:
- Hiểu rõ **từng bước** pipeline đã làm gì.
- Chỉ ra **chỗ nào tốn thời gian** / phụ thuộc nhiều vào LLM.

---

### 1. Ý định & chọn schema

#### 1.1. Phân loại ý định (intent_agent)

Từ state trong log:
- `intent = "data_query"`
- `intent_reasoning`: người dùng “truy vấn dữ liệu liên quan đến số lượng sinh viên theo ngành”.

Nghĩa là:
- `intent_agent` (LLM) đã phân loại câu hỏi thuộc loại **data_query**, nên graph đi nhánh:
  - `START → intent → schema`.

#### 1.2. Vector search schema trong Qdrant (schema_agent – bước 1)

Log:

```text
INFO:httpx:HTTP Request: POST http://nlsql_qdrant:6333/collections/schema_collection/points/query "HTTP/1.1 200 OK"
WARNING:agents.schema_agent:[SchemaAgent] No table >= 0.68. All scores: DotXtnSinhVien=0.557, ..., QuyetDinhThoiHoc=0.475
```

Diễn giải:
1. `schema_agent` nhúng `user_query` bằng OpenAI Embeddings.
2. Gửi vector đó lên Qdrant (`schema_collection`) để tìm các bảng candidate.
3. Qdrant trả nhiều bảng có score ~0.47–0.56, nhưng **không bảng nào ≥ threshold 0.68**.
4. Agent log toàn bộ score và kết luận “No table ≥ 0.68”.

Hệ quả:
- Ở bước vector search thuần túy, **chưa có bảng nào đủ “tự tin”** để dùng luôn.

#### 1.3. Fallback LLM chọn bảng (schema_agent – bước 2)

Log:

```text
WARNING:agents.schema_agent:[SchemaAgent] Only 0 table(s) found via vector search. Falling back to LLM.
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:agents.schema_agent:[SchemaAgent] LLM fallback suggested: ['SinhVien', 'KhoaNganh', 'Nganh', ...] → valid new: [...]
INFO:agents.schema_agent:[SchemaAgent] Final relevant_tables = ['SinhVien', 'KhoaNganh', 'Nganh', ...]
```

Khi vector search “thất bại”:
1. `schema_agent` load **toàn bộ danh sách bảng** từ DB (`_fetch_all_tables()`).
2. Gửi prompt (HUMAN) lên LLM:
   - Câu hỏi người dùng.
   - Danh sách tất cả bảng.
   - Yêu cầu: liệt kê tên bảng **có thể liên quan** (mỗi bảng 1 dòng).
3. LLM trả về một list bảng, sau khi lọc còn các bảng hợp lệ:
   - `SinhVien`, `KhoaNganh`, `Nganh`, `KhoaNganhHocKy`, `SvNganh`, ...
4. Với mỗi bảng đó, agent gọi `_fetch_table_schema(...)`:
   - Lấy danh sách cột, foreign keys, sample rows.

Kết quả đưa vào state:

- `relevant_tables = ['SinhVien', 'KhoaNganh', 'Nganh', ...]`
- `schema_context = [schema chi tiết cho từng bảng]`

=> Bước này dùng **1 call LLM** + **nhiều round-trip DB** nhưng đổi lại có schema chuẩn hơn vector search.

---

### 2. Lập kế hoạch truy vấn (sql_plan_agent)

Log:

```text
INFO:agents.sql_plan_agent:[SQLPlanAgent] Generating reasoning plan for query='Thống kê sinh viên theo từng ngành học'...
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:agents.sql_plan_agent:[SQLPlanAgent] Generated Plan:
### KẾ HOẠCH SQL REASONING CHO CÂU HỎI "THỐNG KÊ SINH VIÊN THEO TỪNG NGÀNH HỌC" ###
...
```

`sql_plan_agent`:
1. Đọc `user_query` + `schema_context`.
2. Render schema thành text (danh sách cột, kiểu, mô tả, rule).
3. Gửi prompt cho LLM để:
   - Chọn các bảng cần dùng: `SinhVien`, `KhoaNganh`, `Nganh`.
   - Xác định columns:
     - `sv.maNganh` (SinhVien), `kn.maNganh`, `kn.ten` (KhoaNganh),
     - `ng.ma`, `ng.ten` (Nganh).
   - Đề xuất không đặt điều kiện WHERE (lấy tất cả).
   - Đề xuất aggregation: `COUNT(DISTINCT sv.ma)`.
   - Đề xuất JOIN, GROUP BY, ORDER BY.
4. LLM trả về một plan chi tiết và gợi ý SQL mẫu.

State sau bước này:
- `query_plan` chứa đúng đoạn text đó (kế hoạch và SQL mẫu).

Đây là **1 call LLM nữa**, chủ yếu giúp tăng “giải thích nội bộ”, nhưng về hiệu năng là thêm latency.

---

### 3. Sinh câu SQL (sql_gen_agent)

Log:

```text
INFO:agents.sql_gen_agent:[SQLGenAgent] attempt=1 query='Thống kê sinh viên theo từng ngành học'
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:agents.sql_gen_agent:[SQLGenAgent] generated_sql=
SELECT 
    "ng"."ten" AS "ten_nganh",
    COUNT(DISTINCT "sv"."ma") AS "so_luong_sinh_vien"
FROM 
    "SinhVien" AS "sv"
JOIN 
    "KhoaNganh" AS "kn" ON "sv"."maNganh" = "kn"."maNganh"
JOIN 
    "Nganh" AS "ng" ON "kn"."maNganh" = "ng"."ma"
GROUP BY 
    "ng"."ten"
ORDER BY 
    "ng"."ten";
```

`sql_gen_agent`:
1. Nhận:
   - `user_query`
   - `schema_context`
   - `query_plan`
   - `retry_count=0`
2. (Tùy config) có thể query Qdrant `few_shot_collection` để lấy ví dụ SQL tương tự.
3. Gửi prompt lớn cho LLM (SQL_GEN_SYSTEM + HUMAN) yêu cầu:
   - Chỉ dùng SELECT.
   - Dùng đúng tên bảng/cột, có `"`.
   - Không join bằng `_id`.
4. LLM trả structured output:
   - `sql` (câu SELECT).
   - `reasoning`.

Trong log:
- SQL sinh ra đúng join 3 bảng, COUNT DISTINCT sinh viên theo ngành.

Đây là **call LLM thứ ba** trong pipeline.

---

### 4. Validate SQL (sql_check_agent)

Hai pha:

1. **Dry-run EXPLAIN:**

```text
INFO:agents.sql_check_agent:[SQLCheckAgent] validating SQL via EXPLAIN dry-run...
INFO:agents.sql_check_agent:[SQLCheckAgent] PASS (EXPLAIN OK). No LLM correction needed.
```

- `sql_check_agent` chạy:
  - Hard safety check (chặn INSERT/DELETE/...).
  - `EXPLAIN {generated_sql}` trên ClickHouse.
- EXPLAIN OK → query hợp lệ về syntax và tên bảng/cột.

2. **Cập nhật state:**

Trong state update cuối cùng:

```text
sql_correction: {'is_valid': True, 'issues': [], 'fixed_sql': '...'}
final_sql: SELECT ...
```

- Agent đánh dấu SQL hợp lệ và set `final_sql` = câu SQL đã sinh.
- Vì EXPLAIN pass, **không cần gọi thêm LLM correction** trong case này.

=> Bước này không thêm LLM call, nhưng thêm **một round-trip EXPLAIN tới DB**.

---

### 5. Thực thi SQL (executor_agent)

Log:

```text
WARNING:agents.executor_agent:[ExecutorAgent] Redis CACHE error: Error 111 connecting to localhost:6379. Connection refused.
INFO:agents.executor_agent:[ExecutorAgent] executing SQL on clickhouse:
SELECT 
    "ng"."ten" AS "ten_nganh",
    COUNT(DISTINCT "sv"."ma") AS "so_luong_sinh_vien"
FROM ...
ORDER BY 
    "ng"."ten"
LIMIT 1000
INFO:agents.executor_agent:[ExecutorAgent] OK — 36 rows in 46.9 ms
WARNING:agents.executor_agent:[ExecutorAgent] Redis SET error: Error 111 connecting to localhost:6379. Connection refused.
```

Các bước:
1. Cache Redis:
   - Thử get theo hash `user_query`.
   - Redis không chạy → warning, bỏ qua.
2. Thêm LIMIT:
   - Vì SQL không có LIMIT, agent thêm `LIMIT 1000` (ClickHouse).
3. Thực thi trên ClickHouse:
   - Thời gian đo được: **~46.9 ms**.
   - Trả về 36 dòng (`ten_nganh`, `so_luong_sinh_vien`).
4. Thử set cache Redis:
   - Lại lỗi vì Redis không chạy.

State sau `EXECUTE`:
- `query_result`: 36 ngành + số sinh viên.
- `row_count = 36`.
- `execution_time_ms ≈ 46.91`.

Đây là phần **nhanh** trong pipeline (chỉ ~50ms).

---

### 6. Sinh chart (chart_agent)

Log:

```text
INFO:agents.chart_agent:[ChartAgent] columns=['ten_nganh', 'so_luong_sinh_vien'], rows=36, forced_chart_type=None
INFO:agents.chart_agent:[ChartAgent] column_profiles:
  - ten_nganh: string (dimension, 36 giá trị duy nhất)
  - so_luong_sinh_vien: integer (measure, 35 giá trị duy nhất)
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:agents.chart_agent:[ChartAgent] chart_type=bar
```

`chart_agent`:
1. Profile cột:
   - `ten_nganh`: dimension string, nhiều giá trị.
   - `so_luong_sinh_vien`: measure integer.
2. Gửi prompt LLM chọn:
   - chart_type.
   - x_axis, y_axis.
3. LLM trả `chart_type = "bar"`, `x_axis="ten_nganh"`, `y_axis="so_luong_sinh_vien"`.
4. Agent reshape data và gộp nhóm nhỏ thành “Khác”.

Đây là **call LLM thứ tư** trong pipeline.

---

### 7. Sinh câu trả lời text (answer_agent)

Log:

```text
INFO:agents.answer_agent:[AnswerAgent] generating answer for 36 rows, has_chart=True
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:agents.answer_agent:[AnswerAgent] answer_format=chart+text
...
answer: Dưới đây là thống kê số lượng sinh viên theo từng ngành học. Bạn có thể xem biểu đồ để có cái nhìn trực quan hơn về dữ liệu này.
answer_format: chart+text
```

`answer_agent`:
1. Nhận:
   - `user_query`
   - `row_count=36`
   - sample của `query_result`
   - `has_chart=True`
2. Gửi prompt LLM để viết:
   - 1 đoạn tóm tắt bằng tiếng Việt.
   - Chọn `answer_format` phù hợp.
3. LLM trả:
   - `answer`: câu mô tả ngắn, dẫn tới chart.
   - `answer_format="chart+text"`.

Đây là **call LLM thứ năm**.

---

### 8. Recommend questions + trả response

Cuối log còn có 1 call `POST /v1/chat/completions` sau bước `ANSWER`:
- Nhiều khả năng từ `utils.recommend.generate_recommend_questions`, tạo các câu hỏi gợi ý tiếp theo.

Sau đó server trả HTTP 200 với payload:
- `answer`
- `answer_format`
- `sql`
- `data`
- `chart_config`, `chart_data`
- (có thể) `recommend_questions`.

---

### 9. Tổng kết số bước & call chính

Cho request “Thống kê sinh viên theo từng ngành học”, pipeline đã:

1. **LLM calls**:
   - intent_agent
   - schema_agent (fallback LLM)
   - sql_plan_agent
   - sql_gen_agent
   - chart_agent
   - answer_agent
   - recommend (nếu bật)

   → khoảng **6–7 lần LLM**.

2. **Embeddings + Qdrant**:
   - 1 lần embedding + query `schema_collection`.
   - Có thể thêm lần embedding ở `sql_gen_agent` cho few-shot (không thể hiện rõ trong log nhưng code hỗ trợ).

3. **DB**:
   - Nhiều lần `_fetch_table_schema` khi fallback LLM trong schema_agent.
   - 1 lần `EXPLAIN` trong sql_check_agent.
   - 1 lần thực thi SQL chính trong executor_agent (~47ms).

4. **Redis**:
   - 1 GET + 1 SET (cùng lỗi `Connection refused`, không ảnh hưởng kết quả nhưng log warning).

Nhìn chung:
- **DB thực thi rất nhanh (~47ms)**.
- **Độ trễ tổng** chủ yếu đến từ:
  - nhiều lần gọi LLM (ít nhất 5 lần cho intent/schema/sql_plan/sql_gen/chart/answer).
  - fallback LLM trong schema vì Qdrant score thấp.

File này có thể dùng làm tham chiếu khi tối ưu để:
- Giảm bớt bước LLM (ví dụ bỏ `sql_plan_agent` với câu hỏi đơn).
- Cải thiện Qdrant/threshold để giảm fallback LLM ở schema_agent.

