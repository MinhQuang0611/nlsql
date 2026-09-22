# NLSQL — Trạng thái hệ thống hiện tại

> Cập nhật: **2026-09-15**. Đây là tài liệu nguồn-chân-lý về luồng chạy thực tế.
>
> **Lưu ý 2026-09-22:** đợt "gọn pipeline" đã đổi sơ đồ §2 và bảng §3 — các node
> `domain_router`, `intent`, `clarification`, `sql_plan` không còn; thay bằng `router`
> và `sql_gen` (có field `plan`); `sql_check`, `chart` không còn gọi LLM; không còn
> checkpointer. Sơ đồ mới xem [README.md](../README.md) và `roadmap.md` Đợt 3.
> Các tài liệu cũ hơn (`architecture.md`, `stream_chat.md`, `nlsql_luong_chay_chi_tiet.md`)
> mô tả kiến trúc **trước** đợt nâng cấp đa DB và streaming, nên có chỗ đã lệch với code.

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Luồng graph đầy đủ](#2-luồng-graph-đầy-đủ)
3. [Vai trò từng node](#3-vai-trò-từng-node)
4. [Kiến trúc đa cơ sở dữ liệu](#4-kiến-trúc-đa-cơ-sở-dữ-liệu)
5. [Hai vòng lặp tự sửa lỗi](#5-hai-vòng-lặp-tự-sửa-lỗi)
6. [API và luồng streaming SSE](#6-api-và-luồng-streaming-sse)
7. [Cấu hình](#7-cấu-hình)
8. [Số liệu đo được](#8-số-liệu-đo-được)
9. [Vấn đề đang mở](#9-vấn-đề-đang-mở)
10. [Roadmap](#10-roadmap)

---

## 1. Tổng quan

Hệ hỏi đáp ngôn ngữ tự nhiên trên cơ sở dữ liệu, tối ưu cho tiếng Việt. Người dùng hỏi,
hệ thống chọn database phù hợp, sinh SQL, thực thi, rồi trả về text / bảng / biểu đồ.

| Thành phần | Công nghệ |
|---|---|
| Orchestration | LangGraph `StateGraph`, 16 node |
| LLM | OpenAI — `gpt-5.4-mini` (mặc định), `gpt-5.4` (riêng cho `sql_gen`) |
| Vector store | Qdrant — `schema_collection_<domain>`, `few_shot_collection_<domain>`, knowledge |
| DB nghiệp vụ | Đa nguồn qua **Domain Registry** — ClickHouse và/hoặc PostgreSQL |
| DB nội bộ | PostgreSQL (lịch sử chat + LangGraph checkpoint) |
| Cache | Redis |
| API | FastAPI, hỗ trợ SSE streaming |
| Frontend | wren-ui (Next.js) |

---

## 2. Luồng graph đầy đủ

```
                              START
                                │
                                ▼
                         ┌──────────┐
                         │   faq    │  khớp FAQ có sẵn → trả lời ngay
                         └────┬─────┘
                  faq_answered│└──────────────► END
                                │
                                ▼
                     ┌──────────────────┐
                     │  domain_router   │  chọn DB (qldt / tcns)
                     └────────┬─────────┘  bỏ qua nếu endpoint đã chỉ định
                                │
                                ▼
                         ┌──────────┐
                         │  intent  │  phân loại ý định
                         └────┬─────┘
          ┌──────────────┬─────┴──────┬──────────────┐
          │              │            │              │
   ambiguous│     greeting/out_of_scope│      data_query / chart_request
          │              │            │       domain_query / schema_question
          ▼              ▼            │       knowledge_query
   ┌──────────────┐  ┌────────┐      │              │
   │clarification │  │ answer │      │       ┌──────┴───────┐
   └──────┬───────┘  └───┬────┘      │       ▼              ▼
          │              │            │  ┌────────┐   ┌───────────┐
          ▼              ▼            │  │ schema │   │ knowledge │  (song song)
         END            END           │  └────┬───┘   └─────┬─────┘
                                      │       └──────┬──────┘
                                      │              ▼
                                      │      ┌────────────────┐
                                      │      │ retrieval_join │
                                      │      └───────┬────────┘
                                      │   knowledge_query │ schema_question
                                      │              ├──────────────► answer
                                      │              ▼
                                      │       ┌────────────┐
                                      │       │  sql_plan  │
                                      │       └──────┬─────┘
                                      │              ▼
                                      │       ┌────────────┐◄──────────┐
                                      │       │  sql_gen   │           │
                                      │       └──────┬─────┘           │
                                      │              ▼                 │
                                      │       ┌────────────┐           │
                                      │       │ sql_check  │  EXPLAIN  │
                                      │       └──┬──────┬──┘           │
                                      │  hợp lệ  │      │ sai cú pháp  │
                                      │          │      └──► inc_retry ┤ (tối đa 3)
                                      │          ▼                     │
                                      │    ┌───────────┐               │
                                      │    │  execute  │               │
                                      │    └─────┬─────┘               │
                                      │          ▼                     │
                                      │    ┌────────────┐              │
                                      │    │ data_check │ kiểm kết quả │
                                      │    └──┬──────┬──┘              │
                                      │  hợp lý│      │ 0 dòng/NULL/lỗi│
                                      │        │      └► inc_data_retry┘ (tối đa 1)
                                      │        ▼
                                      │   ┌─────────┐
                                      │   │  chart  │
                                      │   └────┬────┘
                                      │        ▼
                                      └───►┌────────┐
                                           │ answer │ ──► END
                                           └────────┘
```

Đường đi xấu nhất tốn khoảng **24 super-step**, sát mức mặc định 25 của LangGraph, nên
`recursion_limit` được đặt tường minh **50** ở mọi điểm gọi graph.

---

## 3. Vai trò từng node

| Node | Gọi LLM | Nhiệm vụ |
|---|:---:|---|
| `faq` | có | Đối chiếu FAQ có sẵn. Khớp thì trả lời ngay, bỏ qua toàn bộ pipeline. |
| `domain_router` | có* | Chọn database theo mô tả nghiệp vụ. *Bỏ qua khi endpoint đã gán domain. |
| `intent` | có | Phân loại: `data_query`, `chart_request`, `schema_question`, `domain_query`, `knowledge_query`, `greeting`, `out_of_scope`, `ambiguous`. |
| `schema` | có | Semantic search trên Qdrant lấy bảng liên quan, rồi LLM tỉa bớt. Có fallback sang LLM khi vector search không đạt ngưỡng 0.68. |
| `knowledge` | có | RAG quy định nghiệp vụ (đồng bộ từ Google Sheet). |
| `retrieval_join` | không | Điểm hợp nhất hai nhánh song song. |
| `sql_plan` | có | Lập kế hoạch reasoning trước khi sinh SQL. |
| `sql_gen` | có | Sinh SQL từ plan + schema + few-shot + quy tắc dialect. |
| `sql_check` | có* | `EXPLAIN` dry-run. *Chỉ gọi LLM khi EXPLAIN lỗi, để sửa. |
| `execute` | không | Chạy SQL, cache Redis, giới hạn 1000 dòng. |
| `data_check` | không | Kiểm định **kết quả** (0 dòng / toàn NULL / lỗi). |
| `chart` | có | Data profiling + chọn kiểu biểu đồ, sinh `ChartConfig`. |
| `answer` | có* | Tổng hợp câu trả lời. *Trả thẳng chuỗi soạn sẵn cho `greeting`, `out_of_scope`, `schema_question`, và khi SQL lỗi. |
| `clarification` | có | Sinh câu hỏi làm rõ khi câu hỏi mơ hồ. |
| `inc_retry`, `inc_data_retry` | không | Tăng bộ đếm retry, chặn lặp vô hạn. |

---

## 4. Kiến trúc đa cơ sở dữ liệu

### 4.1. Domain Registry

Trước đây `ACTIVE_DB` là biến global nên **mọi domain buộc phải cùng loại engine**.
Nay mỗi domain tự khai engine của nó (`config.DomainConfig`):

```python
DomainConfig(name="qldt", engine="clickhouse", db_name="qldt", description="...")
```

```env
ACTIVE_DB=clickhouse          # engine mặc định
DOMAINS_ENABLED=qldt,tcns
DOMAIN_ENGINE_QLDT=           # rỗng => dùng ACTIVE_DB
DOMAIN_ENGINE_TCNS=postgres   # override: tcns chạy PostgreSQL trong khi qldt ở ClickHouse
```

`db/connection.py` tạo engine **theo từng domain**: domain ClickHouse dùng sync engine +
HTTP driver, domain PostgreSQL dùng async engine + `AsyncSession`.

### 4.2. Ba mức đa DB

| Mức | Nghĩa | Trạng thái |
|---|---|---|
| 1 | Nhiều DB, người dùng chọn trước qua endpoint `/qldt/chat`, `/tcns/chat` | ✅ |
| 2 | Agent tự route câu hỏi → DB đúng, qua endpoint chung `/chat` | ✅ `domain_router` |
| 3 | Một câu hỏi join chéo nhiều DB | ❌ chưa — xem roadmap |

### 4.3. Prompt theo dialect

`prompts/dialect.py` giữ khối quy tắc SQL riêng cho từng hệ quản trị, chọn theo engine
của **domain đang xử lý**, không theo biến global.

Cái bẫy nguy hiểm nhất được cảnh báo tường minh trong prompt ClickHouse:

```sql
-- SAI: ClickHouse chia hai số nguyên vẫn ra số nguyên, phần thập phân bị cắt
round(countIf(`diem` >= 4.0) * 100 / count(), 2)

-- ĐÚNG: phải ép kiểu trước khi chia
round(toFloat64(countIf(`diem` >= 4.0)) * 100 / count(), 2)
```

Đây là loại lỗi SQL vẫn chạy, vẫn trả về số, chỉ là **số sai** — không công cụ nào bắt được.

---

## 5. Hai vòng lặp tự sửa lỗi

| | `sql_check` | `data_check` |
|---|---|---|
| Kiểm cái gì | Câu SQL (tĩnh) | Kết quả chạy ra |
| Cách kiểm | `EXPLAIN` dry-run | Đọc `query_result`, `row_count`, `executor_error` |
| Bắt được | Sai cú pháp, sai tên cột, thiếu quyền | Lỗi thực thi, 0 dòng, toàn NULL, aggregate NULL |
| Số lần thử lại | 3 | 1 |
| Không bắt được | Lỗi ngữ nghĩa | Chọn nhầm bảng (kết quả vẫn "trông hợp lệ") |

**Vì sao `data_check` chỉ retry 1 lần:** 0 dòng đôi khi *chính là* câu trả lời đúng
("có sinh viên nào GPA > 3.99 không?"). Retry mù chỉ đốt token và có thể sinh ra SQL
sai hơn bản đầu. Hết lượt thì chấp nhận kết quả và để `answer_agent` diễn giải trung thực.

---

## 6. API và luồng streaming SSE

### 6.1. Endpoints

| Endpoint | Domain | Ghi chú |
|---|---|---|
| `POST /api/v1/chat` | tự chọn | Non-stream |
| `POST /api/v1/chat/stream` | tự chọn | SSE |
| `POST /api/v1/qldt/chat[/stream]` | qldt | Gán cứng |
| `POST /api/v1/tcns/chat[/stream]` | tcns | Gán cứng |
| `POST /api/v1/chat_with_table` | — | Giới hạn theo bảng người dùng chọn |

### 6.2. Các event SSE

| Event | Khi nào | Nội dung |
|---|---|---|
| `connected` | Ngay lập tức | Báo đã mở kết nối |
| `node_finish` | Mỗi node xong | `node`, `execution_time_ms`, `state_update` (**chỉ khoá đã đổi**, JSON hợp lệ) |
| `answer_token` | Trong lúc LLM sinh | Một mẩu text của câu trả lời |
| `final_result` | Cuối cùng | `ChatResponse` đầy đủ: answer, sql, data, chart_config… |
| `error` | Khi có ngoại lệ | `detail` |

### 6.3. Thứ tự event — điểm client BẮT BUỘC phải biết

Token được bắn **trong lúc** node `answer` còn đang chạy, nên chúng tới **TRƯỚC**
`node_finish` của chính node đó:

```
... node_finish(chart)
    answer_token  answer_token  answer_token ...
    node_finish(answer)          ◄── tới SAU các token
    final_result
```

> **Client không được xoá text đã stream khi nhận `node_finish`.** Đây từng là bug ở
> wren-ui: `setStreamingAnswer('')` chạy vô điều kiện nên thổi bay toàn bộ câu trả lời
> vừa hiện (giữ được **0 ký tự**). Đã sửa bằng cờ `answerStarted`.

### 6.4. Cơ chế stream token

`astream(stream_mode=["updates", "messages"])`:

- Kênh `updates` → event `node_finish`
- Kênh `messages` → token LLM sinh ra bên trong node

Hai ràng buộc đã xử lý:

1. Kênh `messages` bắn token của **mọi** LLM call, kể cả JSON nội bộ của `intent` và
   `sql_gen`. Phải lọc `meta["langgraph_node"] == "answer"`.
2. `answer_agent` yêu cầu LLM trả JSON `{"answer": "...", "answer_format": "..."}`, nên
   token thô là `'{"'`, `'answer'`, `'":"'`, `'Hi'`, `'ện'`… `utils/json_stream.py` bóc
   dần giá trị field `answer`, chịu được escape và `\uXXXX` bị cắt ngang chunk.

**Đường lui:** câu trả lời soạn sẵn (`greeting`, `out_of_scope`, `schema_question`, lỗi SQL)
và luồng `clarification` không đi qua LLM nên không có token. Khi đó gửi nguyên câu trả lời
trong **một** event `answer_token`, không giả lập gõ phím.

### 6.5. Cách nhận biết streaming có thật sự chạy

Token của LLM bị tách theo **subword**, không theo từ:

```
"Có"  " "  "46"  " ngành"  " Ng"  "ành"  "748"  "020"  "1"
        ▲                    ▲▲▲▲▲▲▲▲▲▲    ▲▲▲▲▲▲▲▲▲▲▲▲▲
   token khoảng trắng    một từ tách đôi   số tách làm 3
```

Code cũ dùng `answer.split(' ')` nên chỉ cho ra từng từ trọn vẹn. Thấy mảnh subword
nghĩa là streaming thật đang chạy.

Trang kiểm chứng: **`http://<host>:8388/static/stream_test.html`** — đọc stream đúng
chuẩn `getReader()`, đóng dấu thời gian thật từng event và tự kết luận STREAM OK / KHÔNG STREAM.

---

## 7. Cấu hình

### Biến môi trường quan trọng

```env
# Bảo mật — chốt chặn SQL ghi. Trước đây suy ra từ APP_ENV nên
# APP_ENV=development vô hiệu hoá chốt ngay trên DB thật.
ALLOW_WRITE_SQL=false

# Domain registry
ACTIVE_DB=clickhouse
DOMAINS_ENABLED=qldt,tcns
DOMAIN_ENGINE_QLDT=
DOMAIN_ENGINE_TCNS=

# Tên database theo engine
CH_DB_NAME_QLDT=qldt
CH_DB_NAME_TCNS=tcns
PG_DB_NAME_QLDT=qldt
PG_DB_NAME_TCNS=tcns
```

### File cấu hình

| File | Vai trò |
|---|---|
| `config/few_shot_<domain>.json` | Ví dụ câu hỏi → SQL, nạp vào Qdrant |
| `config/benchmark_<domain>.json` | Bộ câu hỏi + gold SQL để đo accuracy |
| `prompts/dialect.py` | Quy tắc SQL riêng theo hệ quản trị |

Hai file JSON trên **phải tách biệt**. Trùng câu hỏi thì benchmark chỉ đo khả năng chép
lại ví dụ; `run_bennmark.py` tự cảnh báo khi phát hiện trùng.

### Lệnh thường dùng

```bash
# Nạp few-shot (chạy thật từng ví dụ, loại ví dụ trả 0 dòng)
docker exec nlsql_app python -m scripts.index_few_shot [domain]

# Đo execution accuracy
docker exec nlsql_app python -m scripts.run_bennmark [domain] [--limit N] [--out file.json]
```

---

## 8. Số liệu đo được

### Chất lượng (domain qldt, 12 câu, hai lần chạy độc lập trùng khớp)

```
Chạy được (execution rate) : 12/12 (100%)
Đúng (execution accuracy)  : 11/12 (92%)
Phải retry                 : 0/12
Latency                    : 13-18s/câu ở steady state
```

`retry = 0/12` nghĩa là bộ benchmark hiện tại **quá dễ** để chạm tới các nhánh sửa lỗi —
chưa đo được giá trị thật của `data_check`.

### Streaming (câu trả lời 1.533 ký tự / 514 token)

```
token đầu tiên   : 33.12s
node answer xong : 36.17s   → text hiện sớm hơn 3.05s
ghép token == final_result : đúng (1533 == 1533)
payload           : giảm 79% (25.507 B → 5.351 B)
```

Bản cũ cùng câu này xong ở ~43,7s (chờ 36,17s + ~7,5s gõ phím giả). Bản mới xong ở 36,08s.

---

## 9. Vấn đề đang mở

### 9.1. Domain `tcns` không có bảng nào — CẦN QUYẾT

Database `tcns` tồn tại và kết nối được, nhưng có **0 bảng**. Qdrant lại vẫn giữ
`schema_collection_tcns` với 161 điểm từ lần index cũ. Hệ quả: `domain_router` route
đúng câu hỏi nhân sự sang `tcns`, rồi thất bại ở bước lấy schema.

Đã có cảnh báo lúc khởi động trong `check_db_connection()`. Hai lựa chọn:
nạp dữ liệu cho `tcns`, hoặc đặt `DOMAINS_ENABLED=qldt` cho tới khi có dữ liệu.

### 9.2. Schema linking là điểm yếu lớn nhất

Câu sai duy nhất trong benchmark:

> "Học phần nào có nhiều lượt học nhất?"

| | Bảng chọn | Kết quả |
|---|---|---|
| Agent lần 1 | `LopHocPhan` | `('BAS1106', 321)` |
| Agent lần 2 | `HocPhanCtdt` | (khác) |
| Đúng | `DiemHocPhan` | `('BAS1106', 9995)` |

Hai lần chạy chọn **hai bảng khác nhau**, không lần nào trúng, dù `temperature=0.0`.
SQL sinh ra hoàn toàn hợp lệ, trả 1 dòng không NULL — nên `data_check` **không thể**
bắt được, và đổi model cũng không sửa được: không gì trong hệ thống nói cho LLM biết
"lượt học" nghĩa là `DiemHocPhan`.

Đây là bằng chứng đo được cho thấy bottleneck nằm ở **ngữ nghĩa nghiệp vụ**, không ở
khả năng viết SQL.

### 9.3. LLM không biết giá trị enum thật

Khảo sát domain `qldt`:

| Cột | Giá trị thật |
|---|---|
| `SinhVien.trangThaiHoc` | `Đang học`, `Đã tốt nghiệp`, `Thôi học`, `Chưa phân lớp`, `Bảo lưu` |
| `SinhVien.gioiTinh` | `Nam`, `Nữ`, NULL (8.862 dòng) |
| `SinhVien.quocTich` | `Việt Nam`, NULL (38.906/51.125 dòng), **lẫn ObjectId rác** |

Bộ few-shot đầu tiên viết `WHERE trangThaiHoc = 'DANG_HOC'` — **qua được EXPLAIN** nhưng
trả 0 dòng. Chính vì vậy `scripts/index_few_shot.py` nay **chạy thật** từng ví dụ và loại
bỏ ví dụ trả 0 dòng, thay vì chỉ EXPLAIN.

Chất lượng dữ liệu cần lưu ý: `quocTich` NULL 76% và lẫn ObjectId chưa resolve.

### 9.4. Các điểm nhỏ

- **Agent trả `{**state}` thay vì delta.** LangGraph chỉ cần delta. Đã lọc ở tầng
  `chat.py` (`_delta()`) nên payload không còn phình, nhưng gốc vấn đề vẫn còn ~10 file.
- **`PREDEFINED_FORMULAS` là dead config** — khai báo trong `config.py` nhưng không file
  nào đọc, lại viết theo cú pháp PostgreSQL. Nên xoá hoặc nối vào prompt.
- **`clarification_question` luôn `None`** trong `ChatResponse` dù schema mô tả "client nên
  hiển thị câu này". Không chỗ nào trong `chat.py` set nó; câu hỏi làm rõ hiện đi nhờ qua
  field `answer`.
- **Plan phân quyền chưa thi hành** — `docs/plan_gioi_han_quyen_agent.md` cần quyền admin
  trên `192.168.30.28`.
- **Tài liệu cũ đã lệch** — `architecture.md`, `stream_chat.md`,
  `nlsql_luong_chay_chi_tiet.md` mô tả kiến trúc trước đợt nâng cấp này.

---

## 10. Roadmap

### Ưu tiên 1 — Semantic layer (MDL-lite)

Giải quyết trực tiếp 9.2 và 9.3, hai vấn đề chất lượng lớn nhất.

Thay `TABLE_RULES` (prompt tiếng Việt hardcode trong `config.py`) bằng file khai báo
`config/semantic/<domain>.yml`: entity, relationship, metric, alias tiếng Việt.

Nguồn dữ liệu vàng đã có sẵn: `QLDT_FINAL.xlsx` mô tả **228 bảng bằng tiếng Việt**, và
`TableColumn` trong state đã có sẵn field `excel_vi_name` / `excel_note`.

Điều này biến `"lượt học" = COUNT(DiemHocPhan)` từ *lời khuyên cho LLM* thành *quan hệ
được khai báo* mà LLM không thể sinh sai. Đây cũng là bước mở đường cho đa DB mức 3.

### Ưu tiên 2 — Value profiling vào schema index

Với cột kiểu chuỗi có dưới ~30 giá trị phân biệt, `scripts/index_schema.py` nạp luôn danh
sách giá trị vào payload Qdrant. Rẻ, và bịt đúng lớp lỗi ở 9.3.

### Ưu tiên 3 — Mở rộng benchmark

Từ 12 lên 50-100 câu, lấy từ log người dùng thật. **Phải có câu khó**: nhiều JOIN, lọc
theo enum, khoảng thời gian hiếm dữ liệu — hiện `retry = 0/12` nên chưa đo được giá trị
của `data_check`.

### Ưu tiên 4 — Thi hành plan phân quyền

`docs/plan_gioi_han_quyen_agent.md`: role read-only, view che PII, settings profile,
quota. Cần phối hợp với quản trị `192.168.30.28`.

### Ưu tiên 5 — Dọn nợ kỹ thuật

- Agent trả delta thay vì `{**state}`
- Xoá hoặc nối `PREDEFINED_FORMULAS`
- Set `clarification_question` vào `ChatResponse`
- Cập nhật hoặc đánh dấu các tài liệu đã lệch

### Chưa lên lịch — Đa DB mức 3 (join chéo DB)

**Trước khi làm, phải trả lời:** có câu hỏi nghiệp vụ nào thật sự cần join `qldt` × `tcns`
không? Nếu chỉ là "so sánh số sinh viên và số nhân sự" thì hai query độc lập rồi merge ở
`answer_agent` rẻ hơn vài bậc.

Nếu thật sự cần, lựa chọn thực dụng **không phải** tự viết federation, mà là dùng DuckDB
làm query engine trung gian, hoặc dựng ClickHouse dictionary / remote table.

### Đã cân nhắc và loại bỏ

| Phương án | Lý do loại |
|---|---|
| Đổi orchestrator sang AWEL (DB-GPT) | LangGraph đã là DAG engine; AWEL chỉ hơn ở visualize. Rework lớn, lợi ích nhỏ. |
| Đổi sang SQLCoder / PremSQL | Yếu hơn về tiếng Việt và ClickHouse dialect. Bottleneck là schema linking, không phải khả năng viết SQL. Chỉ cân nhắc nếu ràng buộc là **privacy** (dữ liệu sinh viên có PII). |
| Fine-tuning | Chưa có bộ dữ liệu đủ lớn, và chưa chứng minh được model là bottleneck. |
