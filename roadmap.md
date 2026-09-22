# NLSQL — Roadmap

> Cập nhật: **2026-09-22**.
> Chi tiết kiến trúc và luồng chạy hiện tại: **[docs/TRANG_THAI_HIEN_TAI.md](docs/TRANG_THAI_HIEN_TAI.md)**
> Bản phân tích so sánh ban đầu (2026-09-09), đã lỗi thời nhưng giữ lại để tham chiếu:
> [docs/roadmap_phan_tich_ban_dau_20260909.md](docs/roadmap_phan_tich_ban_dau_20260909.md)

## Đã xong

### Đợt 1 — Nâng cấp đa DB (2026-09-15)

| Việc | Kết quả |
|---|---|
| Domain Registry | Mỗi domain tự khai engine — chạy được cấu hình lai ClickHouse + PostgreSQL |
| `domain_router` node | Đa DB từ mức 1 lên **mức 2**: agent tự chọn DB (7/7 câu test đúng) |
| `data_check` node | Execution-guided self-correction theo PremSQL (7/7 case test đúng) |
| Prompt theo dialect | Sửa lỗi hệ chạy ClickHouse mà prompt dạy PostgreSQL |
| Chốt chặn SQL ghi | `ALLOW_WRITE_SQL=false`, thay cho suy luận sai từ `APP_ENV` |
| Cache key theo domain | Hết trả nhầm kết quả giữa `qldt` và `tcns` |
| Few-shot theo domain | Thay ví dụ e-commerce bằng 10 ví dụ thật, có kiểm chứng |
| Benchmark harness | Đo execution accuracy — baseline **11/12 (92%)** |

### Đợt 2 — Sửa API chat stream (2026-09-15)

| Việc | Kết quả |
|---|---|
| Streaming token thật | `stream_mode=["updates","messages"]` — text hiện sớm hơn 3.05s |
| `utils/json_stream.py` | Bóc dần field `answer` khỏi JSON đang stream (13 test + 600 fuzz) |
| `state_update` hợp lệ | Hết Python repr cắt giữa chừng, client parse được |
| Payload giảm 79% | 25.507 B → 5.351 B |
| Sửa reducer wren-ui | Trước đó FE xoá sạch text vừa stream (giữ được **0 ký tự**) |

### Đợt 3 — Gọn pipeline (2026-09-22)

| Việc | Kết quả |
|---|---|
| Gộp `domain_router` + `intent` + `clarification` → `router` | −1 lượt LLM/câu, −2 node |
| Gộp `sql_plan` vào `sql_gen` (field `plan` trước `sql` trong structured output) | −1 lượt LLM/câu, hết prompt copy-paste |
| Bỏ LLM correction trong `sql_check` | Một vòng sửa lỗi duy nhất; hết prompt ghi cứng PostgreSQL |
| `chart` chọn theo luật từ `column_profiles` | −1 lượt LLM/câu; LLM chỉ khi `chart_request` + dữ liệu mơ hồ |
| `answer` trả text thuần, `answer_format` theo luật | Bỏ `utils/json_stream.py`; stream thẳng |
| Bỏ LangGraph checkpointer | Hết rò state giữa các lượt (`data_retry_count`, `selected_tables`, `query_result`) |
| `knowledge_query` kết thúc tại `knowledge` | Sửa bug `answer_agent` ghi đè câu trả lời từ tài liệu |
| `chat.py` một generator lõi cho stream + non-stream | −300 dòng; `clarification_question` có trong `ChatResponse` |
| `utils/llm.py` | `llm_timeout` / `max_tokens` được truyền thật; bỏ `PREDEFINED_FORMULAS` |
| Đo lại | benchmark 3/3 đúng, **3 lượt LLM/câu** (trước 6–7), latency TB 10,8s (trước 13–18s) |

### Đợt 4 — Schema linking (2026-09-22)

Số liệu trước khi sửa (12 câu benchmark, đo trực tiếp trên Qdrant): bảng đúng có
recall@5 = 6/12; `SinhVien` đứng hạng **18/253** cho câu "Tổng số sinh viên", `Nganh` hạng
26 cho "bao nhiêu ngành đào tạo". Ngưỡng 0.68 không bảng nào vượt qua, và payload không
có `schema_json` nên hạ ngưỡng đơn thuần sẽ KeyError.

| Việc | Kết quả |
|---|---|
| Index hai tầng: `schema_collection_<d>` (text ngắn: tên + mô tả TV) + `schema_columns_<d>` (mỗi cột một điểm) | Hết pha loãng bởi số cột; 253 bảng + 4.266 cột |
| Payload đầy đủ: `schema_json` có tên TV, **502 FK từ Excel** (ClickHouse không có FK), `row_count` | Tên tiếng Việt và đồ thị JOIN lần đầu tới prompt sinh SQL |
| Điểm kết hợp: 0.4·bảng + 0.3·cột tốt nhất + 0.2·từ vựng (bỏ dấu) + 0.1·prior(số dòng) | recall@5: 6 → **10/12**; recall@20: 11/12 |
| Quét từ vựng toàn catalog: bảng khớp nguyên cụm luôn vào ứng viên | `Nganh` hạng 26 → 1 |
| LLM chọn từ ≤20 ứng viên có mô tả + số dòng + cột khớp + liên kết, không trần số bảng | 12/12 chọn đúng, TB 1,1 bảng/câu |
| `TABLE_RULES` gieo quy tắc `DiemHocPhan` (lượt học), `KqhtTichLuy` vs `KqhtHocKy`; bảng có rule luôn hiện với LLM | Giải quyết 3 câu mơ hồ ngữ nghĩa |
| `db/introspect.py` tách khỏi agent; `AsyncQdrantClient` + `aembed_query` | schema node hết block event loop |
| Đo lại (2 lần chạy) | **12/12 đúng cả 2 lần**, 11/12 SQL giống hệt, latency TB **7,1s** (trước 13–18s, 11/12) |

`INDEX_VERSION = 2` trong `scripts/index_schema.py` — startup tự index lại khi thấy collection cũ.

## Việc tiếp theo

### 1. Semantic layer (MDL-lite) — ưu tiên cao nhất

Thay `TABLE_RULES` hardcode bằng `config/semantic/<domain>.yml` khai báo entity,
relationship, metric, alias tiếng Việt. Nguồn có sẵn: `QLDT_FINAL.xlsx` (228 bảng mô tả
tiếng Việt) + field `excel_vi_name` đã có trong state.

**Vì sao ưu tiên cao nhất:** Đợt 4 đã chứng minh cơ chế — ba câu mơ hồ ("lượt học",
"học lực" theo kỳ hay tích luỹ, "tín chỉ tích luỹ") chỉ đúng sau khi có quy tắc nghiệp vụ;
retrieval tốt đến mấy cũng không thay được. `TABLE_RULES` hiện là mầm của glossary, cần
chuyển sang file khai báo để người nghiệp vụ tự bổ sung mà không sửa code.

### 2. Value profiling vào schema index

Nạp danh sách giá trị phân biệt (với cột chuỗi có < ~30 giá trị) vào payload Qdrant.
Bịt lớp lỗi "LLM không biết `trangThaiHoc` nhận giá trị gì" — chính lỗi đã khiến bộ
few-shot đầu tiên viết `'DANG_HOC'` trong khi giá trị thật là `'Đang học'`.

### 3. Mở rộng benchmark lên 50-100 câu

Lấy từ log người dùng thật, **phải có câu khó**. Hiện `retry = 0/12` nghĩa là bộ test
quá dễ để chạm tới các nhánh sửa lỗi.

### 4. Thi hành plan phân quyền

[docs/plan_gioi_han_quyen_agent.md](docs/plan_gioi_han_quyen_agent.md) — role read-only,
view che PII, settings profile, quota. Cần phối hợp với quản trị `192.168.30.28`.

### 5. Dọn nợ kỹ thuật

- Embed câu hỏi **một lần** dùng chung cho faq / knowledge / sql_gen few-shot (schema đã async; 3 node còn lại vẫn embed sync)
- Tỉa cột cho bảng > 40 cột (schema_json đã đủ thông tin để tỉa theo cột khớp)
- Cập nhật `architecture.md`, `stream_chat.md`, `nlsql_luong_chay_chi_tiet.md`, `TRANG_THAI_HIEN_TAI.md` §2–3

## Cần quyết định

**Domain `tcns` có 0 bảng.** DB tồn tại và kết nối được nhưng rỗng, trong khi Qdrant vẫn
giữ 161 điểm schema cũ. `domain_router` sẽ route đúng câu hỏi nhân sự sang đó rồi thất bại.
Chọn: nạp dữ liệu cho `tcns`, hay đặt `DOMAINS_ENABLED=qldt` tạm thời.

**Đa DB mức 3 (join chéo DB).** Trước khi làm phải trả lời: có câu hỏi nghiệp vụ nào thật
sự cần join `qldt` × `tcns` không? Nếu chỉ so sánh hai con số thì hai query độc lập rẻ hơn
nhiều bậc. Nếu cần thật, dùng DuckDB làm engine trung gian thay vì tự viết federation.

## Đã cân nhắc và loại bỏ

| Phương án | Lý do loại |
|---|---|
| AWEL của DB-GPT | LangGraph đã là DAG engine; rework lớn, lợi ích nhỏ |
| SQLCoder / PremSQL | Yếu hơn về tiếng Việt và ClickHouse dialect; bottleneck không nằm ở model. Chỉ cân nhắc nếu ràng buộc là privacy (dữ liệu có PII) |
| Fine-tuning | Chưa đủ dữ liệu, và chưa chứng minh model là bottleneck |
