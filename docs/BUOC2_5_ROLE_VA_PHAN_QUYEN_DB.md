# Bước 2–5 — Tạo role, cấp quyền, tạo user DB cho Agent

> **Yêu cầu gốc (anh Dũng - CNS):**
> *2. Tạo role: `CREATE ROLE agent NOLOGIN`*
> *3. Cấp quyền ghi đọc bảng/view/schema: `GRANT USAGE ON SCHEMA ... TO agent; GRANT SELECT/CREATE/... ON ... TO agent`*
> *4. Tạo user db `CREATE USER` và gán role agent vào user*
> *5. Chỉ cho phép AI Agents truy cập qua USER role agent*

**Ngày khảo sát:** 11/09/2026
**Phạm vi:** Bước 2, 3, 4, 5. Bước 1 xem tài liệu `BUOC1_DANH_SACH_BANG_VA_VIEW.md`
**Trạng thái:** Chưa bắt đầu — 0%

---

## 1. Vì sao gộp 4 bước vào một tài liệu

Bước 2 (`CREATE ROLE`) **không thể làm riêng lẻ** — một role không có `GRANT`
thì không có quyền gì, không ai gán vào thì không ai dùng được. Bốn bước này là
một chuỗi liên hoàn, phải làm trọn gói mới có tác dụng:

```
Bước 2: tạo role  →  Bước 3: cấp quyền cho role
                            ↓
Bước 5: app dùng user đó  ←  Bước 4: tạo user, gán role
```

Thời gian thực hiện cả 4 bước: **khoảng nửa ngày.**

---

## 2. Hiện trạng (đo thực tế)

### PostgreSQL — `192.168.30.28:16543`

```
=== Danh sách role/user ===
  ript      super=True   login=True
```

**Chỉ có duy nhất một tài khoản: `ript`, và nó là SUPERUSER.**

| Kiểm tra | Kết quả |
|---|---|
| Số role/user (không tính `pg_*` hệ thống) | **1** |
| `ript` là superuser | **Có** |
| `ript` có createrole / createdb | **Có** |
| Số bảng trong schema `public` | 221 |
| `PUBLIC` có `USAGE` trên schema `public` | **Có** (mặc định Postgres) |
| Role read-only cho agent | **Không có** |

### ClickHouse — `192.168.30.28:18123`

```
=== USERS ===  clickhouse
=== ROLES ===  (không có role nào)
```

| Kiểm tra | Kết quả |
|---|---|
| Số user | **1** (`clickhouse`) |
| Số role | **0** |
| Quyền của `clickhouse` | Toàn quyền `ON *.*` **WITH GRANT OPTION** |
| Có `CREATE USER`, `DROP USER`, `ROLE ADMIN` | **Có** |

### Kết luận hiện trạng

**Mức đáp ứng bước 2–5: 0%.**

Agent đang kết nối bằng chính tài khoản quản trị duy nhất của cả hai DB.
Không có bất kỳ sự tách biệt nào giữa "tài khoản quản trị" và "tài khoản agent".

---

## 3. Rủi ro hiện tại

Đây là phần cần nêu rõ để đánh giá mức độ ưu tiên.

### 3.1. Chuỗi rủi ro đang mở

```
Internet / mạng nội bộ
      ↓  (không có authentication — mọi endpoint /api/v1/* đều public)
FastAPI :8388
      ↓  (LLM sinh SQL tự do)
Regex chặn lệnh ghi
      ↓  ← LỚP CHẶN DUY NHẤT
PostgreSQL với quyền SUPERUSER
```

### 3.2. Lớp chặn ghi đang bị vô hiệu hoá

`agents/executor_agent.py:71`:

```python
if settings.app_env != "development" and _DANGEROUS_PATTERN.search(final_sql):
```

`.env` đang đặt `APP_ENV=development` (kèm ghi chú *"doi thanh production khi len prod"*).
→ Điều kiện **luôn false** → **mọi lệnh ghi đều lọt qua executor.**

Còn lại một lớp regex ở `agents/sql_check_agent.py:26`, nhưng regex chỉ lọc được
**động từ** (`INSERT|UPDATE|DELETE|DROP|...`), không lọc được **đối tượng**:

| Câu lệnh | Regex chặn? | Thực tế |
|---|---|---|
| `DROP TABLE SinhVien` | Có | — |
| `SELECT * FROM bang_luong` | **Không** | SELECT thuần, qua cửa |
| `SELECT * FROM pg_authid` | **Không** | Đọc được hash mật khẩu (vì là superuser) |
| `COPY ... TO PROGRAM 'sh -c ...'` | **Không** | Không có trong pattern |
| `SELECT pg_read_file('/etc/passwd')` | **Không** | Không có trong pattern |
| `WHERE ghi_chu LIKE '%update%'` | **Có** | Chặn nhầm (false positive) |

Với quyền superuser, ba dòng giữa đều thực thi được.

### 3.3. Vì sao bước 2–5 là biện pháp đúng

Regex nằm ở **tầng ứng dụng** — phụ thuộc code viết đúng, và hiện đang tắt.
`GRANT SELECT` nằm ở **tầng database** — DB tự cưỡng chế, code có sai cũng không
vượt qua được.

Sau khi hoàn thành bước 2–5: dù LLM sinh `DROP TABLE`, dù regex thủng hoàn toàn,
DB vẫn trả về `permission denied`.

---

## 4. Các việc cần làm

### Việc 2.1 — Tạo role và cấp quyền (PostgreSQL)

```sql
-- Bước 2: tạo role, NOLOGIN (role thuần, không đăng nhập trực tiếp)
CREATE ROLE agent_qldt_ro NOLOGIN;

-- Bước 3: cấp quyền — CHỈ SELECT, không CREATE/INSERT/UPDATE/DELETE
GRANT USAGE ON SCHEMA public TO agent_qldt_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_qldt_ro;

-- Bảng tạo mới sau này cũng tự có quyền SELECT
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO agent_qldt_ro;

-- Bước 4: tạo user thật và gán role
CREATE USER nlsql_agent_qldt LOGIN PASSWORD '<mật khẩu mạnh>';
GRANT agent_qldt_ro TO nlsql_agent_qldt;

-- Giới hạn tài nguyên
ALTER ROLE nlsql_agent_qldt SET statement_timeout = '30s';
ALTER ROLE nlsql_agent_qldt CONNECTION LIMIT 10;
```

**Lưu ý quan trọng về `GRANT SELECT/CREATE` trong yêu cầu gốc:**
Yêu cầu ghi *"GRANT SELECT/ CREATE/..."*. Đề xuất **chỉ cấp `SELECT`, không cấp
`CREATE`** — agent chỉ cần đọc để trả lời câu hỏi. Cấp `CREATE` sẽ cho phép agent
tạo bảng/view trong DB sản xuất, không cần thiết và làm mất ý nghĩa của việc hạ quyền.

**Về `REVOKE ... FROM PUBLIC`:**
Postgres mặc định cấp `USAGE` trên schema `public` cho vai trò `PUBLIC` (đã xác
nhận: `has_schema_privilege('public','public','USAGE') = True`). Nếu muốn siết
chặt hơn thì cân nhắc:

```sql
REVOKE ALL ON SCHEMA public FROM PUBLIC;
```

> **Cảnh báo:** lệnh này ảnh hưởng **mọi user khác** đang dùng DB, không chỉ agent.
> Chỉ chạy khi đã xác nhận không có hệ thống nào khác phụ thuộc. Nếu không chắc
> thì **bỏ qua** — việc tạo user read-only riêng đã đủ đạt mục tiêu.

---

### Việc 2.2 — Tạo role và cấp quyền (ClickHouse)

Cú pháp khác Postgres:

```sql
-- Bước 2: tạo role
CREATE ROLE agent_qldt_ro;

-- Bước 3: cấp quyền chỉ đọc
GRANT SHOW TABLES, SELECT ON qldt.* TO agent_qldt_ro;

-- Bước 4: tạo user và gán role
CREATE USER nlsql_agent_qldt
    IDENTIFIED WITH sha256_password BY '<mật khẩu mạnh>'
    SETTINGS max_execution_time = 30, readonly = 1;

GRANT agent_qldt_ro TO nlsql_agent_qldt;
SET DEFAULT ROLE agent_qldt_ro TO nlsql_agent_qldt;
```

**Khác biệt cần lưu ý so với Postgres:**

| | PostgreSQL | ClickHouse |
|---|---|---|
| `NOLOGIN` | Có, role thuần | **Không có** — role mặc định không đăng nhập được |
| Đơn vị phân quyền | schema | database |
| Gán role mặc định | Tự động | Phải `SET DEFAULT ROLE` thủ công |
| Giới hạn thời gian | `statement_timeout` | `max_execution_time` |

`readonly = 1` là lớp chặn thứ hai ở cấp setting, độc lập với `GRANT`.

---

### Việc 2.3 — Nếu có domain `tcns`

Lặp lại 2.1/2.2 với role `agent_tcns_ro` và user `nlsql_agent_tcns` riêng.

**Vì sao phải tách theo domain, không dùng chung một role:**
Hiện `/qldt/chat` và `/tcns/chat` đều public, không authentication. Nếu dùng chung
một user có quyền cả hai DB thì không chặn được truy cập chéo — người chỉ nên xem
dữ liệu đào tạo vẫn hỏi được dữ liệu nhân sự bằng cách đổi URL.

> **Lưu ý:** hiện `tcns` có **0 bảng** trong ClickHouse. Cần xác nhận domain này
> đã dùng chưa trước khi tạo role cho nó.

---

### Việc 2.4 — Đổi cấu hình ứng dụng (bước 5)

Sửa `.env`:

```diff
- PG_DB_USER=ript
- PG_DB_PASSWORD=<mật khẩu cũ>
+ PG_DB_USER=nlsql_agent_qldt
+ PG_DB_PASSWORD=<mật khẩu mới>

- CH_DB_USER=clickhouse
- CH_DB_PASSWORD=<mật khẩu cũ>
+ CH_DB_USER=nlsql_agent_qldt
+ CH_DB_PASSWORD=<mật khẩu mới>
```

**Chỉ sửa cấu hình, không sửa một dòng code nào.**

**Nếu muốn tách credential theo domain** (khuyến nghị, nhưng cần sửa code):
`config.py:16-33` hiện chỉ có **một** cặp user/password dùng chung cho cả `qldt`
và `tcns`. Để mỗi domain một user riêng thì phải thêm biến và sửa
`get_database_url()` tại `config.py:120`.

---

### Việc 2.5 — Kiểm thử

Sau khi đổi, chạy kiểm tra:

```sql
-- Phải THÀNH CÔNG
SELECT COUNT(*) FROM "SinhVien";

-- Phải THẤT BẠI với "permission denied"
CREATE TABLE test_x (id int);
DROP TABLE "SinhVien";
UPDATE "SinhVien" SET hoTen = 'x';
INSERT INTO "SinhVien" VALUES (...);
```

Kiểm tra thêm ở tầng ứng dụng:
- Hỏi một câu bình thường qua `/api/v1/qldt/chat` → vẫn trả lời được
- Xem `error.log` có lỗi quyền bất thường không

---

## 5. Bảng tổng hợp

| # | Việc | Người làm | Công sức | Rủi ro |
|---|---|---|---|---|
| 2.1 | Role + user read-only (Postgres) | Anh chạy SQL | 1 giờ | Thấp |
| 2.2 | Role + user read-only (ClickHouse) | Anh chạy SQL | 1 giờ | Thấp |
| 2.3 | Lặp cho domain `tcns` (nếu dùng) | Anh chạy SQL | 0,5 giờ | Thấp |
| 2.4 | Đổi `.env` | Anh | 15 phút | Thấp |
| 2.5 | Kiểm thử | Anh + tôi | 1 giờ | — |

**Tổng: khoảng nửa ngày.**

### Vì sao rủi ro thấp

| | |
|---|---|
| Có sửa bảng/dữ liệu của DB không | **Không** — chỉ `CREATE ROLE`, `CREATE USER`, `GRANT` |
| Có ảnh hưởng `ript` / `clickhouse` không | **Không** — tạo tài khoản mới, không đụng tài khoản cũ |
| Có ảnh hưởng hệ thống khác đang dùng DB không | **Không** (trừ khi chạy `REVOKE ... FROM PUBLIC`) |
| Cách rollback | Đổi lại `.env` về user cũ — tức thì |

**Khuyến nghị: tạo user MỚI, không hạ quyền `ript`.**
`ript` là tài khoản duy nhất của DB, nhiều khả năng đang được hệ thống khác dùng.
Hạ quyền nó có thể làm gãy thứ không liên quan. Tạo `nlsql_agent_qldt` riêng thì
không ảnh hưởng gì.

---

## 6. Mức đáp ứng sau khi hoàn thành

| Bước | Trước | Sau |
|---|---|---|
| 2. Tạo role | 0% | **100%** |
| 3. Cấp quyền | 0% | **~90%** (chỉ SELECT, chưa có view — thuộc bước 1) |
| 4. Tạo user + gán role | 0% | **100%** |
| 5. Agent chỉ truy cập qua user role | 0% | **~85%** (chưa tách credential theo domain) |
| *Toàn bộ 5 bước* | *~8%* | *~55%* |

**Giải quyết được:**
- Agent không còn chạy dưới superuser
- Lệnh ghi bị DB chặn tuyệt đối, không phụ thuộc regex đang tắt
- Không đọc được `pg_authid`, không dùng được `pg_read_file()`, `COPY TO PROGRAM`

**Chưa giải quyết** (thuộc bước 1 và ngoài 5 bước):
- 64 cột nhạy cảm vẫn đọc được (cần view — bước 1)
- Agent vẫn thấy toàn bộ 253 bảng (cần allowlist — bước 1)
- Chưa phân biệt account nào hỏi được bảng nào (cần login + `user_permissions`)

---

## 7. Quan hệ với bước 1

Hai phần **độc lập, làm song song được**:

| | Bước 1 | Bước 2–5 |
|---|---|---|
| Nội dung | Danh sách bảng + view che cột | Role, quyền, user |
| Chặn gì | Đọc sai bảng / sai cột | Ghi, và thao tác quyền cao |
| Phụ thuộc | Cần nghiệp vụ duyệt (2–3 ngày) | **Không phụ thuộc ai** |
| Công sức | 2–3 ngày | Nửa ngày |

**Đề xuất: làm bước 2–5 trước.** Lý do:
- Không phải chờ nghiệp vụ duyệt danh sách
- Nửa ngày, đưa mức đáp ứng từ 8% lên ~55%
- Bịt lỗ hổng nghiêm trọng nhất (superuser + lớp chặn ghi đang tắt)

Trong lúc chờ nghiệp vụ duyệt danh sách bảng cho bước 1, bước 2–5 đã xong.

---

## Phụ lục — Nguồn số liệu

Đo trực tiếp ngày 11/09/2026:

| Số liệu | Cách lấy |
|---|---|
| `ript` superuser, 1 role duy nhất | `SELECT rolname, rolsuper, rolcanlogin FROM pg_roles` |
| 221 bảng schema `public` | `information_schema.tables` |
| `PUBLIC` có `USAGE` trên `public` | `has_schema_privilege('public','public','USAGE')` |
| ClickHouse: 1 user, 0 role | `SHOW USERS` / `SHOW ROLES` |
| Quyền `clickhouse` WITH GRANT OPTION | `SHOW GRANTS` |

**File liên quan:**
- `agents/executor_agent.py:71` — lớp chặn ghi đang bị vô hiệu hoá
- `agents/sql_check_agent.py:26` — regex chặn lệnh ghi
- `config.py:16-33` — khai báo user/password DB
- `config.py:120` — `get_database_url()`, chỗ cần sửa nếu tách credential theo domain
- `.env` — biến môi trường cần đổi
