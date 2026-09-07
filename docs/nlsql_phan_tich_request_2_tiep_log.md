## Phân tích log request 2: “Các ngành học nào có số lượng sinh viên cao nhất?”

File này phân tích chuỗi log bạn cung cấp (bắt đầu từ `STEP FINISHED: SCHEMA` cho câu hỏi này) để mô tả:
1) Pipeline đã đi qua những node nào  
2) Mỗi node dùng tài nguyên gì (LLM/embedding/Qdrant/DB)  
3) Chỗ nào thường làm chậm và chỗ nào có thể gây dư tải hoặc giảm chất lượng

---

### 1) Schema step: Qdrant semantic search thất bại → fallback LLM

Log quan trọng:

```text
INFO:agents.schema_agent:[SchemaAgent] Qdrant semantic search for: 'Các ngành học nào có số lượng sinh viên cao nhất?'
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/embeddings ...
INFO:httpx:HTTP Request: POST http://nlsql_qdrant:6333/.../points/query "HTTP/1.1 200 OK"
WARNING:agents.schema_agent:[SchemaAgent] No table >= 0.68. All scores: ... 0.440 ... 0.389 ...
WARNING:agents.schema_agent:[SchemaAgent] Only 0 table(s) found via vector search. Falling back to LLM.
INFO:agents.schema_agent:[SchemaAgent] LLM fallback suggested: [...] → valid new: [...]
INFO:agents.schema_agent:[SchemaAgent] Final relevant_tables = ['KhoaNganh', 'SinhVien', ...]
```

Diễn giải:
- `schema_agent` luôn nhúng query bằng OpenAI embeddings (log thấy call `/v1/embeddings`).
- Qdrant trả các bảng có score thấp hơn threshold:
  - threshold trong code: `SCORE_THRESHOLD = 0.68`
  - score cao nhất quan sát được trong log: khoảng `0.440`
- Vì không bảng nào qua ngưỡng → agent gọi LLM để “bù” danh sách bảng liên quan.

Kết quả của bước `SCHEMA` (đầu vào cho các bước sau):
- `relevant_tables` = 8 bảng:
  - `KhoaNganh`, `SinhVien`, `KhoaNganhHocKy`, `DangKyChuyenNganhSinhVien`,
  - `DangKyChuyenNganhKhoaNganh`, `SinhVienHocKy`, `SvKhoaNganh`, `Nganh`
- `schema_context` chứa schema chi tiết + sample_rows (truncated trong log, nhưng vẫn là payload lớn vào LLM ở bước kế tiếp).

Nhận xét hiệu năng/dư tải:
- Dù cuối cùng câu SQL sử dụng chủ yếu `KhoaNganh` + `SinhVien`, schema step vẫn fetch/schema toàn bộ 8 bảng.
- Điều này có thể làm chậm vì:
  - tăng round-trip DB khi gọi `_fetch_table_schema`
  - tăng kích thước prompt đầu vào cho `sql_plan_agent`, `sql_gen_agent`

---

### 2) SQL Plan step: LLM đưa plan + yêu cầu WHERE/ORDER/LIMIT

Log:

```text
INFO:agents.sql_plan_agent:[SQLPlanAgent] Generating reasoning plan ...
INFO:agents.sql_plan_agent:[SQLPlanAgent] Generated Plan: ...
... WHERE sv.trangThaiHoc = 'Đang học'
... ORDER BY so_luong_sinh_vien DESC
... LIMIT 10
```

Diễn giải:
- `sql_plan_agent` đọc `user_query` + `schema_context`.
- LLM lập kế hoạch:
  - tables: `KhoaNganh` join `SinhVien`
  - column: `ten`, `maNganh` (join) và đếm `COUNT(DISTINCT ma)`
  - filter: chỉ tính `SinhVien` đang học (`trangThaiHoc = 'Đang học'`)
  - sort giảm dần theo số lượng
  - limit top 10

Trong log router, `query_plan` sau bước `SQL_PLAN` chứa đúng kế hoạch trên (có kèm SQL mẫu).

---

### 3) SQL Generation step: LLM sinh câu SQL từ plan

Log:

```text
INFO:agents.sql_gen_agent:[SQLGenAgent] attempt=1 query='Các ngành học nào có số lượng sinh viên cao nhất?'
INFO:agents.sql_gen_agent:[SQLGenAgent] generated_sql=
SELECT "KhoaNganh"."ten" AS "ten_nganh",
       COUNT(DISTINCT "SinhVien"."ma") AS "so_luong_sinh_vien"
FROM "KhoaNganh"
JOIN "SinhVien" ON "KhoaNganh"."maNganh" = "SinhVien"."maNganh"
WHERE "SinhVien"."trangThaiHoc" = 'Đang học'
GROUP BY "KhoaNganh"."ten"
ORDER BY "so_luong_sinh_vien" DESC
LIMIT 10;
```

Diễn giải:
- Dù `schema_context` có nhiều bảng, LLM tối ưu plan SQL bằng cách chỉ dùng 2 bảng cần thiết.
- Điều này có nghĩa:
  - bước schema đã “nặng prompt” hơn cần thiết
  - nhưng bước sql_gen đã tự prune trong câu SQL.

---

### 4) SQL Check step: EXPLAIN pass (không gọi LLM correction)

Log:

```text
INFO:agents.sql_check_agent:[SQLCheckAgent] validating SQL via EXPLAIN dry-run...
INFO:agents.sql_check_agent:[SQLCheckAgent] PASS (EXPLAIN OK). No LLM correction needed.
```

Diễn giải:
- Không có vòng retry, `retry_count = 0`.
- Không có LLM sửa SQL.

---

### 5) Execute step: ClickHouse chạy SQL top 10 (~67 ms)

Log:

```text
WARNING:agents.executor_agent:[ExecutorAgent] Redis CACHE error: Error 111 connecting to localhost:6379. Connection refused.
INFO:agents.executor_agent:[ExecutorAgent] executing SQL on clickhouse: ... LIMIT 10
INFO:agents.executor_agent:[ExecutorAgent] OK — 10 rows in 67.6 ms
WARNING:agents.executor_agent:[ExecutorAgent] Redis SET error: Error 111 ...
```

Điểm đáng chú ý:
- Query execution nhanh: `~67.6 ms`.
- Redis không chạy tại môi trường này:
  - chỉ ảnh hưởng cache (warning), không làm thay đổi kết quả.

Kết quả DB (`query_result`):
- 10 dòng “top ngành” với `so_luong_sinh_vien = 10101` **bằng nhau** cho tất cả ngành trong top 10.

=> Đây là hiện tượng dữ liệu/tính toán:
- Hoặc do câu lệnh join/aggregation đang tạo ra giá trị giống nhau cho nhiều `KhoaNganh.ten` (ví dụ nhiều bản ghi `KhoaNganh` khác nhau nhưng cùng `maNganh` và join mapping khiến count trùng).
- Hoặc dữ liệu thật có tie lớn (nhưng thường ít gặp “top 10 đều y hệt”).

---

### 6) Chart step: profile 10 rows → LLM chọn bar chart

Log:

```text
INFO:agents.chart_agent:[ChartAgent] columns=['ten_nganh', 'so_luong_sinh_vien'], rows=10
INFO:agents.chart_agent:[ChartAgent] chart_type=bar
```

Diễn giải:
- `column_profiles` cho thấy `so_luong_sinh_vien` có `n_unique = 1` (một giá trị duy nhất).
- Chart bar vẫn được chọn, nhưng về mặt trực quan có thể không “informative” vì mọi cột có cùng height.

---

### 7) Answer step: LLM tóm tắt theo kết quả

Log:

```text
INFO:agents.answer_agent:[AnswerAgent] generating answer for 10 rows, has_chart=True
...
answer: Các ngành học có số lượng sinh viên cao nhất đều thuộc lĩnh vực Công nghệ thông tin, với mỗi ngành có số lượng sinh viên là 10,101. ...
```

Diễn giải:
- LLM đọc 10 dòng top ngành và suy ra “đều thuộc lĩnh vực Công nghệ thông tin”.
- Tóm tắt phù hợp với dữ liệu output (vì 10 tên đều là các biến thể IT trong log).

---

## 8) Kết luận: các nguyên nhân chính ảnh hưởng performance/quality trong request này

### 8.1. Hiệu năng (chậm ở đâu?)
- Nút chính làm tăng thời gian ở request này là **schema_agent fallback**:
  - Qdrant score không qua ngưỡng → phải gọi LLM để chọn bảng.
  - sau đó fetch schema cho nhiều bảng, tăng kích thước prompt cho LLM.
- Các bước DB thực thi rất nhanh:
  - `67.6 ms` cho query (vẫn nhanh).

### 8.2. Dư tải prompt
- `relevant_tables` có 8 bảng nhưng SQL cuối chỉ dùng 2 bảng.
- Điều này gợi ý có thể tối ưu:
  - hoặc giảm số bảng fetch khi fallback
  - hoặc dùng bước “prune nhanh” trước khi đưa toàn bộ schema_context vào `sql_plan_agent`.

### 8.3. Rủi ro correctness (top 10 đều bằng nhau)
- Hiện tượng `COUNT(DISTINCT sv.ma) = 10101` lặp lại trong top 10 là dấu hiệu đáng kiểm tra:
  - có thể do join `KhoaNganh.maNganh = SinhVien.maNganh` đang ánh xạ “tương đối” đúng nhưng `ten` đang phân rã ở mức khác (nhiều dòng khác tên nhưng cùng `maNganh`)
  - hoặc do dữ liệu “một maNganh tương ứng nhiều ten KhoaNganh” làm tie lớn.

---

## 9) Gợi ý tối ưu gắn trực tiếp với log này

1. **Giảm fallback LLM trong schema_agent**:
   - Tối ưu embeddings/Qdrant collection (threshold, embed_text, payload schema_json mismatch nếu còn).
2. **Giới hạn schema_context đầu vào LLM**:
   - Khi fallback chọn nhiều bảng, chỉ giữ top K theo score hoặc top K do LLM đề xuất (ví dụ 3–5 bảng).
3. **Prune bảng trước sql_plan_agent**:
   - Gợi ý: sau khi LLM chọn bảng, bước logic tự xác định “bảng nào chắc chắn cần cho join maNganh” rồi loại phần còn lại.
4. **Kiểm tra correctness của “top ngành”**:
   - Thêm bước sanity check: so sánh `COUNT(DISTINCT sv.ma)` theo `maNganh` và xem mapping sang `KhoaNganh.ten` có nhiều bản ghi gây tie không.

