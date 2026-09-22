# Đánh giá phân quyền: Ai được hỏi bảng nào, DB nào

> **Yêu cầu gốc (anh Dũng - CNS):**
> *"Xem chỗ phân quyền ai được hỏi bảng nào, DB nào hãy đánh giá cái này"*

**Ngày khảo sát:** 11/09/2026
**Phạm vi:** Toàn hệ thống — từ endpoint API tới tầng database
**Tài liệu chi tiết từng bước:** `BUOC1_*.md` … `BUOC5_*.md`

---

## 1. Kết luận

**Hiện tại hệ thống KHÔNG CÓ phân quyền. Mức đáp ứng: ~8%.**

Không phải "phân quyền yếu" mà là **không tồn tại**:

| Câu hỏi | Câu trả lời hiện tại |
|---|---|
| Ai được dùng agent? | **Bất kỳ ai** — không có đăng nhập |
| Ai được hỏi DB nào? | **Bất kỳ ai hỏi DB nào cũng được** — chỉ cần đổi URL |
| Ai được hỏi bảng nào? | **Bất kỳ ai hỏi bảng nào cũng được** — cả 253 bảng |
| Agent chạy dưới quyền gì? | **Superuser** |

Con số 8% đến từ hai lớp regex chặn lệnh ghi — mà một trong hai **đang bị tắt**.

---

## 2. Hiện trạng theo từng tầng

### 2.1. Tầng API — không có xác thực

Quét toàn bộ code tìm `jwt|oauth|bearer|authenticate|current_user|HTTPBearer`:
**0 kết quả** trong code ứng dụng.

Kiểm tra `Depends()` trong mọi router: **không có dependency xác thực nào.**
`main.py` chỉ có duy nhất `CORSMiddleware`.

Toàn bộ endpoint đều public:

```
POST /api/v1/chat                POST /api/v1/chat/stream
POST /api/v1/qldt/chat           POST /api/v1/qldt/chat/stream
POST /api/v1/tcns/chat           POST /api/v1/tcns/chat/stream
POST /api/v1/chat_with_table     POST /api/v1/qldt/chat_with_table
POST /api/v1/tcns/chat_with_table
GET  /api/v1/tables?domain=...
```

**Hệ quả — domain là tham số do client chọn, không phải thuộc tính của người dùng:**

```
Người chỉ nên xem dữ liệu đào tạo (QLDT)
      ↓  đổi URL từ /qldt/chat → /tcns/chat
Truy cập tự do dữ liệu nhân sự (TCNS)
```

Thêm nữa, `CORSMiddleware` đặt `allow_origins=["*"]` kèm `allow_credentials=True`
(`main.py:110-118`).

### 2.2. `user_id` là trường client tự khai

`api/schemas/chat.py:19`:

```python
user_id: Optional[str] = Field(None, description="ID của người dùng (tuỳ chọn...)")
```

Giá trị này được ghi thẳng vào bảng `conversations` (`api/routers/chat.py:44`)
mà không kiểm chứng.

**Nghĩa là audit log hiện tại không có giá trị pháp lý** — bất kỳ ai cũng khai
được `user_id` tuỳ ý, kể cả mạo danh người khác.

### 2.3. Tầng database — agent chạy bằng tài khoản quản trị

Đo trực tiếp trên DB:

**PostgreSQL `192.168.30.28:16543`:**
```
Login roles : ript  (rolsuper=True, rolcreaterole=True, rolcreatedb=True)
```
Chỉ có **một** tài khoản, và là **superuser**.

**ClickHouse `192.168.30.28:18123`:**
```
USERS : clickhouse    ROLES : (không có role nào)
GRANT ... ON *.* TO clickhouse WITH GRANT OPTION
```

| Hạng mục | Hiện trạng |
|---|---|
| Role read-only cho agent | **Không có** |
| Số `GRANT` cấp cho agent | **0** |
| View nghiệp vụ | **0** |
| Database khác trên cùng server | `postgres`, `ript`, `vbcc` — agent đọc được hết |

### 2.4. Chặn lệnh ghi chỉ bằng regex — và đang tắt

Hai lớp regex giống nhau: `agents/executor_agent.py:20-23` và
`agents/sql_check_agent.py:26-29`.

**Lớp ở executor bị vô hiệu hoá:**

```python
if settings.app_env != "development" and _DANGEROUS_PATTERN.search(final_sql):
```

`.env` đặt `APP_ENV=development` (kèm ghi chú *"doi thanh production khi len prod"*)
→ điều kiện **luôn false** → mọi lệnh ghi lọt qua.

`docker-compose.prod.yml` nạp đúng file `.env` này qua `env_file`, nên deploy prod
sẽ mang theo cấu hình lỏng.

**Regex chỉ lọc động từ, không lọc đối tượng:**

| Câu lệnh | Regex chặn? | Với quyền superuser |
|---|---|---|
| `DROP TABLE SinhVien` | Có | — |
| `SELECT * FROM bang_luong` | **Không** | Đọc được |
| `SELECT * FROM pg_authid` | **Không** | **Đọc được hash mật khẩu** |
| `SELECT pg_read_file('/etc/passwd')` | **Không** | **Đọc được file hệ thống** |
| `COPY ... TO PROGRAM 'sh -c ...'` | **Không** | **Thực thi lệnh OS** |
| `WHERE ghi_chu LIKE '%update%'` | Có | Chặn nhầm |

### 2.5. Không kiểm soát bảng được truy cập

`selected_tables` từ client (`api/schemas/chat.py:24`) đi thẳng vào
`agents/schema_agent.py:216-222` không qua allowlist:

```python
if selected_tables:
    schema_context = [await _fetch_table_schema(domain, t) for t in selected_tables]
```

Tên bảng được nội suy chuỗi vào SQL tại `agents/schema_agent.py:103`:
`'SELECT * FROM "{table}" LIMIT 3'` — client kiểm soát được phần này.

`GET /api/v1/tables` còn liệt kê sẵn toàn bộ bảng cho người dùng ẩn danh.

### 2.6. Ba đường rò rỉ phụ

| Đường | Vấn đề | Vị trí |
|---|---|---|
| **Redis cache** | Key là `sha256(user_query)` — **không có domain, không có user**. Hai domain hỏi trùng câu sẽ dùng chung kết quả | `executor_agent.py:83` |
| **`sample_rows`** | Chạy `SELECT * ... LIMIT 3` rồi gửi **3 dòng dữ liệu thật** (có thể gồm lương/CCCD) sang OpenAI mỗi lần hỏi | `schema_agent.py:142` |
| **Google Sheet log** | Ghi nguyên văn câu hỏi + SQL ra Sheet ngoài | `chat.py:156-166` |

Điểm Redis đáng lưu ý: **kể cả sau khi làm xong toàn bộ 5 bước, lỗ hổng này vẫn
xuyên thủng phân quyền** — kết quả trả về từ cache trước khi chạm tới DB.

---

## 3. Số liệu hiện trạng

Đo trực tiếp ngày 11/09/2026:

| Chỉ số | Giá trị |
|---|---|
| Bảng trong ClickHouse `qldt` | **253** |
| Bảng có metadata mô tả | 228 |
| **Bảng không có metadata** (gồm `Auth`, `DataPartitionUser`…) | **57** |
| Tổng số cột | 3.075 |
| Cột nhạy cảm ước tính | **64** (2,1%) trong **25 bảng** |
| Bảng `tcns` | **0** (trống) |
| Endpoint có xác thực | **0** |
| Role read-only | **0** |
| View nghiệp vụ | **0** |

---

## 4. Chấm điểm theo 5 bước của anh Dũng

| # | Yêu cầu | Đáp ứng | Ghi chú |
|---|---|---|---|
| 1 | Danh sách bảng / tạo view nghiệp vụ | **0%** | Agent thấy cả 253 bảng, 0 view |
| 2 | `CREATE ROLE agent NOLOGIN` | **0%** | Không có role nào |
| 3 | `GRANT USAGE / SELECT` | **0%** | Không có GRANT nào |
| 4 | `CREATE USER` + gán role | **0%** | Dùng `ript` / `clickhouse` sẵn có |
| 5 | Agent chỉ truy cập qua user role agent | **0%** | Một credential dùng chung |
| — | *(ngoài 5 bước)* Chặn lệnh ghi | **~40%** | Có regex, nhưng yếu và đang tắt |

**Tổng: ~8%.**

---

## 5. Điểm quan trọng: 5 bước KHÔNG trả lời hết câu hỏi

Câu hỏi gốc là *"ai được hỏi bảng nào, DB nào"*. Cần phân biệt:

| | 5 bước (role/GRANT/view) | Phân quyền theo account |
|---|---|---|
| Trả lời | **Agent** được chạm bảng nào | **Ai** được hỏi bảng nào |
| Phạm vi | Toàn hệ thống, một mức chung | Từng account, khác nhau |
| Có khái niệm account | **Không** | Có |
| Nằm ở đâu | DB nguồn `192.168.30.28` | DB nội bộ (container `db`) |

**5 bước không phân biệt được account** — vì nó không có khái niệm người dùng.
Sau khi làm xong cả 5 bước, mọi người vào hệ thống vẫn hỏi được y hệt nhau.

Muốn *"account A hỏi bảng X, account B hỏi bảng Y"* thì cần thêm:
- Đăng nhập (JWT) — **bắt buộc**, vì `user_id` hiện client tự khai
- Bảng `users` + `user_permissions` ở DB nội bộ
- Chặn ở 3 điểm trong code: lọc schema, parse SQL đối chiếu allowlist, lọc `/tables`

Hai phần này **bổ sung nhau, không thay thế nhau**:

```
253 bảng
   ↓ 5 bước      (rào chung: bỏ bảng hệ thống, che cột nhạy cảm)
~171 bảng + 25 view
   ↓ account     (khóa từng phòng)
account A: 12 bảng   |   account B: 5 bảng
```

---

## 6. Lộ trình khắc phục

| GĐ | Nội dung | Công sức | Đạt | Phụ thuộc |
|---|---|---|---|---|
| **0** | Vá gấp: bật chặn ghi, thêm domain vào cache key, lọc `sample_rows` | 1–2 giờ | 8% → 15% | Không |
| **1** | Bước 2,3,4,5: role + user read-only + đổi `.env` | **Nửa ngày** | → **55%** | Không |
| **2** | Bước 1: allowlist bảng + view che 64 cột | 2–3 ngày | → **85%** | **Chờ nghiệp vụ duyệt** |
| **3** | Đăng nhập + `user_permissions` (phân quyền theo account) | 1–2 tuần | → **95%** | Không |

### Đề xuất thứ tự

**Làm giai đoạn 0 và 1 trước** — tổng cộng khoảng một ngày, đưa từ 8% lên 55%.
Đây là phần hiệu quả nhất trên mỗi giờ bỏ ra, và **không phải chờ ai duyệt**.

Giai đoạn 2 chờ nghiệp vụ duyệt danh sách bảng/cột nên khởi động sớm để chạy song song.

Giai đoạn 3 là phần trả lời trọn vẹn câu hỏi *"ai được hỏi bảng nào"*.

### Thuận lợi

Đã kiểm tra: `ript` là **superuser**, `clickhouse` có **WITH GRANT OPTION**.
→ **Làm được toàn bộ 5 bước ngay, không cần xin quyền ai.**

Các bước 2–5 **không sửa bảng hay dữ liệu nào** — chỉ `CREATE ROLE`, `CREATE USER`,
`GRANT`. Rollback bằng cách đổi lại `.env`.

---

## 7. Rủi ro hiện tại — cần nêu rõ

Chuỗi rủi ro đang mở:

```
Mạng (không xác thực, CORS *)
      ↓
FastAPI :8388  — mọi endpoint public
      ↓
LLM sinh SQL tự do
      ↓
Regex chặn ghi  ← LỚP DUY NHẤT, và lớp ở executor ĐANG TẮT
      ↓
PostgreSQL quyền SUPERUSER  /  ClickHouse toàn quyền
```

Với quyền superuser, một câu SQL lách được regex có thể: đọc hash mật khẩu
(`pg_authid`), đọc file hệ thống (`pg_read_file`), thực thi lệnh OS
(`COPY TO PROGRAM`), hoặc xoá bảng.

**Giai đoạn 1 (nửa ngày) cắt đứt chuỗi này** — dù regex thủng hoàn toàn, DB vẫn
từ chối mọi lệnh ghi và mọi truy cập ngoài phạm vi.

---

## Phụ lục — Nguồn số liệu

Đo trực tiếp ngày 11/09/2026:

| Số liệu | Cách lấy |
|---|---|
| 0 endpoint có xác thực | `grep -rniE "jwt\|oauth\|bearer\|current_user\|HTTPBearer"` |
| 0 dependency auth | `grep -rnE "Depends\("` trong `api/routers/*.py` |
| `ript` superuser | `SELECT rolname,rolsuper FROM pg_roles` |
| ClickHouse 1 user, 0 role | `SHOW USERS` / `SHOW ROLES` |
| 253 bảng / 0 view | `SHOW TABLES FROM qldt`; `information_schema.tables` |
| 64 cột nhạy cảm / 25 bảng | Quét từ khoá trên `QLDT_FINAL.xlsx` |
| 4 database: `postgres,qldt,ript,vbcc` | `SELECT datname FROM pg_database` |

**File liên quan:**

| File | Vấn đề |
|---|---|
| `main.py:110-118` | CORS `allow_origins=["*"]` + credentials |
| `api/schemas/chat.py:19` | `user_id` client tự khai |
| `api/schemas/chat.py:24` | `selected_tables` không validate |
| `api/routers/tables.py:48` | Liệt kê toàn bộ bảng cho ẩn danh |
| `agents/executor_agent.py:71` | Lớp chặn ghi bị vô hiệu hoá |
| `agents/executor_agent.py:83` | Cache key thiếu domain/user |
| `agents/schema_agent.py:103` | Nội suy tên bảng vào SQL |
| `agents/schema_agent.py:142` | `sample_rows` gửi dữ liệu thật sang OpenAI |
| `agents/schema_agent.py:216` | `selected_tables` không qua allowlist |
| `agents/sql_check_agent.py:26` | Regex chặn ghi |
| `config.py:51-56` | Một credential dùng chung 2 domain |
| `.env` | `APP_ENV=development`, khai trùng `CH_DB_NAME_TCNS` |
