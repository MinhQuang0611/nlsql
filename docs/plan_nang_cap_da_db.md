# Plan nâng cấp: hệ hỏi đáp đa DB

> Trạng thái: **ĐANG THỰC THI**. Ngày lập: 2026-09-15.
> Cơ sở: so sánh với Vanna, DB-GPT, WrenAI, SQLCoder, PremSQL, NL2SQL-LangGraph.

## Nguyên tắc chọn việc

Không đổi orchestrator (LangGraph đã là DAG engine, đổi sang AWEL là rework lớn lợi ích nhỏ).
Không đổi model (SQLCoder/PremSQL yếu hơn về tiếng Việt và ClickHouse dialect; bottleneck
của hệ này là schema linking + business semantics, không phải khả năng viết cú pháp SQL).

Chỉ lấy 3 thứ: **execution-guided self-correction** (PremSQL), **semantic layer**
(WrenAI/MDL), **governance** (Vanna v2) — và sửa các lỗi đang chảy máu trước.

## Thứ tự thi hành

Sắp theo phụ thuộc kỹ thuật, không theo mức độ hấp dẫn.

| # | Việc | Vì sao đứng ở đây | File |
|---|---|---|---|
| 1 | Bỏ bypass bảo mật ở executor | Độc lập, đang là lỗ hổng sống trên DB thật | `agents/executor_agent.py`, `config.py` |
| 2 | Fix `.env` trùng `CH_DB_NAME_TCNS` | Độc lập, 1 dòng, đang trỏ sai DB | `.env`, `.env.example` |
| 3 | Thêm `domain` vào `AgentState` | Tiền đề cho mọi việc dưới; hiện đang dùng chui qua `.get()` | `graph/state.py` |
| 4 | Domain registry (engine/dialect theo từng domain) | **Nền tảng**. Mọi việc 5-9 đều đọc registry này | `config.py`, `db/connection.py` |
| 5 | Prompt theo dialect | Phụ thuộc (4) để biết dialect. Đang chạy ClickHouse mà prompt ghi PostgreSQL | `prompts/sql_gen.py`, `prompts/sql_plan.py` |
| 6 | Cache key gồm domain + db + SQL | Phụ thuộc (4). Đang trả nhầm kết quả giữa qldt/tcns | `agents/executor_agent.py` |
| 7 | Few-shot tách theo domain | Phụ thuộc (4). Đang seed ví dụ e-commerce vô nghĩa | `scripts/index_few_shot.py`, `agents/sql_gen_agent.py` |
| 8 | `data_check` node (execution-guided) | Phụ thuộc (3). Đây là cơ chế học từ PremSQL | `agents/data_check_agent.py`, `graph/builder.py` |
| 9 | `domain_router` node | Phụ thuộc (4)+(3). Đưa đa DB từ mức 1 lên mức 2 | `agents/domain_router_agent.py`, `graph/builder.py` |
| 10 | Benchmark harness | Làm cuối vì cần (1-9) ổn định để đo, nhưng file golden nên điền song song | `scripts/run_bennmark.py` |

Ngoài phạm vi đợt này (cần input nghiệp vụ hoặc quyết định kiến trúc riêng):

- **Semantic layer / MDL-lite** — thay `TABLE_RULES` bằng file khai báo entity/relationship/metric,
  sinh từ `QLDT_FINAL.xlsx`. Là bước mở đường cho cross-DB join.
- **Cross-DB join (đa DB mức 3)** — chỉ làm khi xác nhận có câu hỏi nghiệp vụ thật sự cần
  join qldt × tcns. Nếu chỉ là "so sánh 2 con số" thì 2 query độc lập rẻ hơn nhiều bậc.
- **Plan phân quyền** — đã có `docs/plan_gioi_han_quyen_agent.md`, thi hành riêng vì cần
  quyền admin trên `192.168.30.28`.

## Ba mức đa DB

| Mức | Nghĩa | Trước đợt này | Sau đợt này |
|---|---|---|---|
| 1 | Nhiều DB, người dùng chọn trước qua endpoint | ✅ | ✅ |
| 2 | Agent tự route câu hỏi → DB đúng | ❌ | ✅ (việc 9) |
| 3 | Một câu hỏi join chéo nhiều DB | ❌ | ❌ (ngoài phạm vi) |

---

## Kết quả thực thi (2026-09-15)

### Đã xong 10/10 việc

| # | Việc | Thay đổi thực tế |
|---|---|---|
| 1 | Bỏ bypass bảo mật | `ALLOW_WRITE_SQL` (mặc định `false`) thay cho suy luận từ `APP_ENV` |
| 2 | Fix `.env` | `CH_DB_NAME_QLDT` + `CH_DB_NAME_TCNS`, bỏ `CH_DB_NAME=warehouse` không ai đọc |
| 3 | `domain` vào state | `domain`, `domain_reasoning`, `data_retry_count` |
| 4 | Domain registry | `DomainConfig`, `get_domain_engine()`, engine tạo theo từng domain |
| 5 | Prompt theo dialect | `prompts/dialect.py` — khối quy tắc riêng cho ClickHouse / PostgreSQL |
| 6 | Cache key | `sha256(engine\|domain\|db_name\|sql)` thay cho `sha256(user_query)` |
| 7 | Few-shot theo domain | `few_shot_collection_<domain>`, seed thật thay ví dụ e-commerce |
| 8 | `data_check` node | Execution-guided self-correction, retry tối đa 1 lần |
| 9 | `domain_router` node | Endpoint chung `/chat` tự chọn DB — đa DB lên mức 2 |
| 10 | Benchmark harness | `scripts/run_bennmark.py` đo execution accuracy |

### Bug phát hiện thêm trong lúc làm (không có trong plan ban đầu)

1. **Few-shot chưa bao giờ chạy.** `sql_gen_agent` gate bằng
   `if settings.qdrant_url and settings.qdrant_api_key`. Qdrant local không đặt API key
   nên `qdrant_api_key = None`, toàn bộ khối few-shot bị bỏ qua im lặng. Đã sửa: chỉ
   gate theo `qdrant_url`.

2. **Seed few-shot là ví dụ e-commerce.** `orders`, `products`, `customers` — không bảng
   nào tồn tại trong DB này. Nếu khối few-shot từng chạy, nó đã bơm nhiễu vào mọi prompt.

3. **Prompt dạy sai hệ quản trị.** `ACTIVE_DB=clickhouse` nhưng cả `sql_gen` lẫn `sql_plan`
   đều mở đầu bằng "chuyên gia SQL cho PostgreSQL", bắt buộc bọc double quote và dùng hàm
   ngày tháng của Postgres.

4. **ClickHouse chia số nguyên bị cắt.** Mọi công thức tỉ lệ / phần trăm đều sai nếu không
   `toFloat64()` trước khi chia — đây là cái bẫy dialect nguy hiểm nhất vì SQL vẫn chạy,
   vẫn trả về số, chỉ là số sai. Đã đưa cảnh báo tường minh kèm ví dụ đúng/sai vào
   `prompts/dialect.py`.

   Ghi chú: `PREDEFINED_FORMULAS.ty_le_dat` trong `config.py` viết theo cú pháp Postgres và
   cũng dính lỗi này, **nhưng nó là dead config** — không file nào đọc tới (`grep -rn
   PREDEFINED_FORMULAS` chỉ ra đúng một dòng khai báo). Nên nó không gây sai số liệu hiện
   tại. Cần xoá hoặc nối vào prompt, chứ để nguyên thì sẽ thành bẫy cho người sửa sau.

5. **`check_db_connection` fail-all.** Một domain hỏng làm cả hàm ném exception → app không
   khởi động được. Nay kiểm tra từng domain độc lập, trả `degraded` thay vì `error`.

6. **`recursion_limit` sát hạn mức.** Thêm `domain_router` + `data_check` đẩy đường đi xấu
   nhất (3 lần retry `sql_check` + 1 lần retry `data_check`) lên ~24 super-step, trong khi
   mặc định của LangGraph là **25**. Chỉ còn margin 1 bước — một nhánh retry nữa là
   `GraphRecursionError` ném thẳng ra người dùng. Đã đặt `recursion_limit: 50` tường minh
   ở cả 2 điểm gọi graph trong `api/routers/chat.py` và trong benchmark.

7. **Domain `tcns` rỗng.** Database `tcns` TỒN TẠI trên ClickHouse (kết nối OK, khác với
   khảo sát ngày 2026-09-08 trong `plan_gioi_han_quyen_agent.md`) nhưng có **0 bảng**.
   Trong khi đó Qdrant vẫn giữ `schema_collection_tcns` với 161 điểm từ lần index cũ.
   Hệ quả: `domain_router` sẽ route đúng câu hỏi nhân sự sang `tcns`, Qdrant trả về tên
   bảng, rồi `_fetch_table_schema` không tìm thấy bảng nào → câu hỏi thất bại.

   Đã thêm cảnh báo lúc khởi động trong `check_db_connection()`. **Cần quyết:** hoặc nạp
   dữ liệu cho `tcns`, hoặc đặt `DOMAINS_ENABLED=qldt` cho tới khi có dữ liệu. Để nguyên
   như hiện tại thì endpoint chung `/chat` sẽ trả lời sai cho mọi câu hỏi nhân sự.

### Bài học từ chính quá trình seed dữ liệu

Bộ few-shot đầu tiên tôi viết có `WHERE trangThaiHoc = 'DANG_HOC'`. Câu này **qua được
EXPLAIN** nhưng trả về 0 dòng, vì giá trị thật trong DB là `'Đang học'`. Tương tự
`gioiTinh` thật là `'Nam'`/`'Nữ'` chứ không phải `'NAM'`/`'NU'`.

Đây đúng là loại lỗi mà `sql_check_agent` (chỉ EXPLAIN) không thể bắt và `data_check_agent`
sinh ra để bắt — một minh hoạ trực tiếp cho lý do việc 8 là cần thiết. Vì vậy
`scripts/index_few_shot.py` nay **chạy thật** từng ví dụ chứ không chỉ EXPLAIN, và loại bỏ
ví dụ trả về 0 dòng.

### Giá trị enum thật (khảo sát 2026-09-15, domain qldt)

| Cột | Giá trị thật |
|---|---|
| `SinhVien.trangThaiHoc` | `Đang học` (32.423), `Đã tốt nghiệp` (17.394), `Thôi học` (1.198), `Chưa phân lớp` (105), `Bảo lưu` (5) |
| `SinhVien.gioiTinh` | `Nam` (29.802), `Nữ` (12.461), NULL (8.862) |
| `SinhVien.quocTich` | `Việt Nam` (11.826), NULL (38.906), **và một số ObjectId rác** (`644895111150f5714f2adccd`…) |
| `KqhtTichLuy.tongSoTinChi` | max = 52, trung bình ≈ 20 |

Hai vấn đề chất lượng dữ liệu cần biết: `quocTich` có 38.906/51.125 dòng NULL và lẫn
ObjectId chưa resolve; `gioiTinh` NULL 8.862 dòng. Câu hỏi thống kê theo hai cột này sẽ
cho số liệu lệch nếu không xử lý NULL.

## Baseline đo được (2026-09-15, domain qldt, 12 câu)

Hai lần chạy độc lập cho kết quả trùng khớp:

```
Chạy được (execution rate) : 12/12 (100%)
Đúng (execution accuracy)  : 11/12 (92%)
Phải retry                 : 0/12
Latency               : ~13-18s/câu ở steady state
```

`Phải retry = 0/12` nghĩa là ở bộ câu hỏi này, cả `sql_check` lẫn `data_check` đều không
phải kích hoạt lần nào. Điều đó KHÔNG chứng minh `data_check` vô dụng — nó chỉ cho thấy
bộ benchmark hiện tại quá dễ để chạm tới các nhánh sửa lỗi. Muốn đo được giá trị thật của
việc 8, bộ câu hỏi cần thêm các câu khó: nhiều JOIN, lọc theo giá trị enum, khoảng thời
gian hiếm dữ liệu.

Về latency: câu đầu tiên mất 120-196s vì cold start (build graph, introspect schema,
warm-up embedding). Từ câu thứ 2 trở đi ổn định ở 12-18s. Con số "trung bình 53.5s" mà
script in ra bị cold start kéo lên, không phản ánh trải nghiệm thật của người dùng.

### Câu sai duy nhất — và vì sao nó quan trọng

> "Học phần nào có nhiều lượt học nhất? Trả về mã học phần và số lượt."

| | Bảng dùng | Kết quả |
|---|---|---|
| Agent, lần chạy 1 | `LopHocPhan` | `('BAS1106', 321)` |
| Agent, lần chạy 2 | `HocPhanCtdt` | (khác) |
| Gold | `DiemHocPhan` | `('BAS1106', 9995)` |

Lỗi **lặp lại ở cả hai lần chạy**, nhưng điều đáng chú ý hơn: hai lần agent chọn **hai
bảng khác nhau**, và không lần nào trúng `DiemHocPhan`. Dù `llm_temperature=0.0`, việc
chọn bảng vẫn dao động — vì bước schema retrieval trả về nhiều bảng đều "hợp lý về mặt
ngữ nghĩa vector" và không có tín hiệu nào phân định. Đây là dấu hiệu kinh điển của
schema linking thiếu ràng buộc, không phải của model yếu. Và nó KHÔNG phải
lỗi cú pháp SQL — câu lệnh agent sinh ra hoàn toàn hợp lệ, chạy được, trả về đúng 1 dòng
với giá trị không NULL. Đây là lỗi **schema linking**: cụm "lượt học" ánh xạ được sang hai
bảng đều hợp lý (`LopHocPhan` = lớp học phần mở ra, `DiemHocPhan` = bản ghi điểm tức lượt
học thật sự), và không có gì trong hệ thống nói cho LLM biết cái nào mới đúng nghiệp vụ.

Ba hệ quả cần rút ra:

1. **`data_check_agent` không bắt được lớp lỗi này** — và về nguyên tắc là không thể.
   Kết quả có 1 dòng, không NULL, không lỗi. Mọi heuristic dựa trên hình dạng kết quả đều
   sẽ cho qua. Đây là giới hạn thật của việc 8, cần nói rõ chứ không nên kỳ vọng quá.

2. **Đổi model không sửa được.** SQLCoder hay PremSQL cũng không có cách nào biết
   "lượt học" nghĩa là `DiemHocPhan` — thông tin đó không nằm trong schema, chỉ nằm trong
   đầu người làm nghiệp vụ.

3. **Đây chính là lý do cần semantic layer.** Khai báo `lượt học = COUNT(DiemHocPhan)`
   ở tầng MDL biến câu hỏi mơ hồ thành xác định. Kết quả đo này là bằng chứng thực nghiệm
   cho thấy bottleneck của hệ thống nằm ở ngữ nghĩa nghiệp vụ, không nằm ở khả năng
   viết SQL — nên semantic layer đáng ưu tiên hơn mọi việc tối ưu model.

## Việc tiếp theo được đề xuất

1. **Value profiling đưa vào schema index.** Đây là thứ WrenAI gọi là value profiling và
   là nguyên nhân gốc của lớp lỗi ở trên: LLM không biết `trangThaiHoc` nhận giá trị gì.
   Cách rẻ nhất: với cột kiểu chuỗi có ít hơn ~30 giá trị phân biệt, `index_schema.py`
   nạp luôn danh sách giá trị vào payload Qdrant.
2. **Semantic layer / MDL-lite** — thay `TABLE_RULES` bằng file khai báo.
3. **Mở rộng bộ benchmark** lên 50-100 câu từ log người dùng thật.
4. **Thi hành `docs/plan_gioi_han_quyen_agent.md`** (cần quyền admin trên `192.168.30.28`).

## Cách chạy lại

```bash
# 1. Nạp lại few-shot (có kiểm chứng: chạy thật, loại ví dụ trả 0 dòng)
docker exec nlsql_app python -m scripts.index_few_shot          # tất cả domain
docker exec nlsql_app python -m scripts.index_few_shot qldt     # một domain

# 2. Đo execution accuracy
docker exec nlsql_app python -m scripts.run_bennmark qldt
docker exec nlsql_app python -m scripts.run_bennmark qldt --limit 5
docker exec nlsql_app python -m scripts.run_bennmark --out /tmp/bench.json
```

## File cấu hình mới

| File | Vai trò |
|---|---|
| `config/few_shot_<domain>.json` | Ví dụ câu hỏi → SQL, nạp vào Qdrant |
| `config/benchmark_<domain>.json` | Bộ câu hỏi + gold SQL để đo accuracy |
| `prompts/dialect.py` | Khối quy tắc SQL riêng theo hệ quản trị |

Hai file JSON trên **phải giữ tách biệt** — trùng câu hỏi thì benchmark chỉ đo khả năng
chép lại ví dụ. `run_bennmark.py` tự cảnh báo nếu phát hiện trùng.

## Biến môi trường mới

```env
ALLOW_WRITE_SQL=false        # chốt chặn SQL ghi, thay cho việc suy ra từ APP_ENV
DOMAINS_ENABLED=qldt,tcns    # domain nào được bật
DOMAIN_ENGINE_QLDT=          # rỗng => dùng ACTIVE_DB; đặt để override riêng
DOMAIN_ENGINE_TCNS=
```

Nhờ `DOMAIN_ENGINE_*`, hệ thống nay chạy được cấu hình lai — ví dụ `qldt` trên ClickHouse
còn `tcns` trên PostgreSQL — điều mà biến global `ACTIVE_DB` trước đây không cho phép.

---

# Phụ lục: sửa API chat stream (2026-09-15)

Transport SSE vốn đã hoạt động — events bắn tuần tự qua cả backend lẫn FE proxy.
Vấn đề nằm ở hành vi, gồm 4 điểm đã sửa.

## 1. `answer_token` từ giả thành thật

**Trước:** `answer_agent` sinh xong toàn bộ câu trả lời, rồi `chat.py` mới `split(' ')`
và bắn từng từ kèm `sleep(0.03)`. Người dùng nhìn màn hình trống suốt thời gian sinh,
rồi nhận một hiệu ứng đánh máy hậu kỳ. Với câu trả lời 200 từ, riêng phần `sleep` cộng
thêm 6 giây — bật streaming làm CHẬM hơn không bật.

**Sau:** `astream(stream_mode=["updates", "messages"])`. Kênh `messages` bắn token LLM
ngay trong lúc node đang chạy, không phải sửa code agent nào.

Hai ràng buộc phải xử lý:

- Kênh `messages` bắn token của **mọi** LLM call, kể cả JSON nội bộ của `intent` và
  `sql_gen`. Phải lọc `meta["langgraph_node"] == "answer"`.
- `answer_agent` yêu cầu LLM trả JSON `{"answer": "...", "answer_format": "..."}`, nên
  token thô là `'{"'`, `'answer'`, `'":"'`, `'Hi'`, `'ện'`… Bắn nguyên xi thì client
  thấy cả cú pháp JSON. Đã viết `utils/json_stream.py` — máy trạng thái bóc dần giá trị
  của một field, chịu được escape và `\uXXXX` bị cắt ngang chunk (13 unit test +
  600 lần fuzz cắt ngẫu nhiên đều đúng).

Có đường lui: câu trả lời soạn sẵn (`greeting`, `out_of_scope`, `schema_question`,
lỗi SQL) và luồng `clarification` không đi qua LLM nên không có token — khi đó gửi
nguyên câu trả lời trong một event duy nhất, không giả lập gõ phím.

## 2. `state_update` trở thành JSON hợp lệ

**Trước:** `{k: str(v)[:500]}` → Python repr (dấu nháy đơn), cắt đúng ký tự thứ 500,
thường là giữa chừng một token: `"...{'name': 'ma', 'type': 'Nullable(St"`.
`json.loads()` lên chuỗi này **thất bại**.

**Sau:** `_json_safe()` giữ nguyên cấu trúc lồng nhau, chỉ cắt ở mức từng chuỗi và
từng phần tử, nên kết quả luôn parse được.

## 3. Payload giảm 79%

**Trước:** 25.507 B cho câu trả lời dài 26 ký tự. Payload mỗi event tăng đơn điệu
228 B → 3.478 B vì hầu hết agent `return {**state, ...}` nên "update" chính là toàn
bộ state, lặp lại 13 lần.

**Sau:** 5.351 B. Hàm `_delta()` trong `chat.py` chỉ giữ khoá thực sự đổi giá trị.
Cách này sửa được triệu chứng **mà không phải đụng vào ~10 file agent** — việc đổi
agent sang trả delta thật vẫn nên làm, nhưng không còn gấp.

## 4. Bỏ delay nhân tạo, thêm header chống buffer

- Bỏ `asyncio.sleep(0.05)` sau mỗi node (13 × 50 ms) và `sleep(0.03)` mỗi từ.
- Thêm `X-Accel-Buffering: no` + `Connection: keep-alive` vào cả 3 `StreamingResponse`.
  Thiếu header này thì nginx đặt trước cổng 8388 sẽ gom cả response rồi mới trả.

## 5. Lỗi kéo theo ở frontend — bắt buộc phải sửa cùng

`wren-ui/src/pages/stream/index.tsx` gọi `setStreamingAnswer('')` **vô điều kiện**
mỗi khi nhận `node_finish`. Trước đây vô hại vì token luôn tới sau tất cả `node_finish`.

Sau khi bật streaming thật, thứ tự cuối stream là:

```
tok tok tok tok tok  N:answer  final_result
```

Token của node `answer` tới **trước** `node_finish` của chính nó, nên lệnh reset thổi
bay toàn bộ text vừa hiện. Mô phỏng lại reducer của FE trên stream thật:

| | Text giữ được |
|---|---|
| FE bản cũ | **0 ký tự** — bị xoá sạch |
| FE bản mới | 554 ký tự, khớp `final_result` |

Đã sửa: thêm cờ `answerStarted`, chỉ reset khi câu trả lời chưa bắt đầu stream.
Đồng thời bỏ `setTimeout(r, 80)` trong vòng đọc reader — nó chặn cả vòng lặp nên
làm trễ luôn các token đến sau.

## Đo lường sau khi sửa

Câu trả lời dài 1.533 ký tự (514 token):

```
token đầu tiên   : 33.12s
token cuối       : 36.08s
node answer xong : 36.17s   → text bắt đầu hiện sớm hơn 3.05s
ghép lại == final_result: đúng (1533 == 1533)
```

Bản cũ với cùng câu này: người dùng chờ tới 36.17s mới thấy chữ đầu tiên, rồi mất
thêm ~7,5s gõ phím giả → xong ở ~43,7s. Bản mới xong ở 36,08s.

Regression sweep 5 luồng (`data_query`, `greeting`, `out_of_scope`, endpoint `qldt`,
endpoint `tcns`): mọi event parse được JSON, chuỗi token luôn khớp `final_result`.

## File đụng tới

| File | Thay đổi |
|---|---|
| `utils/json_stream.py` | **mới** — bóc dần field chuỗi từ JSON đang stream |
| `api/routers/chat.py` | `_sse()`, `_json_safe()`, `_delta()`, kênh `messages`, bỏ sleep, header |
| `wren-ui/src/pages/stream/index.tsx` | cờ `answerStarted`, bỏ delay 80 ms |
