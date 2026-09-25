# Bước 4 — Tạo user DB và gán role agent vào user

> **Yêu cầu gốc (anh Dũng - CNS):**
> *"4. Tạo user db `CREATE USER` và gán role agent vào user."*

**Ngày khảo sát:** 11/09/2026
**Phạm vi:** Chỉ bước 4. Bước 1/2/3/5 xem các tài liệu tương ứng.
**Trạng thái:** Chưa bắt đầu — 0%

---

## 1. Hiện trạng (đo thực tế)

### PostgreSQL `192.168.30.28:16543`

```
Login roles          : ript  (connlimit=-1, không hạn dùng)
password_encryption  : scram-sha-256
ssl                  : off
max_connections      : 100
server_version       : 15.14
```

### ClickHouse `192.168.30.28:18123`

```
USERS : clickhouse
ROLES : (không có role nào)
```

### Bảng đánh giá

| Hạng mục | Hiện trạng |
|---|---|
| Số user đăng nhập được (Postgres) | **1** — `ript` |
| User riêng cho agent | **Không có** |
| Giới hạn số kết nối của `ript` | **-1** (không giới hạn) |
| Hạn sử dụng mật khẩu | **Không có** |
| Mã hoá mật khẩu | `scram-sha-256` (tốt) |
| SSL | **off** — mật khẩu truyền dạng không mã hoá trên mạng |

**Mức đáp ứng bước 4: 0%.**

Agent dùng chung tài khoản quản trị duy nhất của DB. Không có sự tách biệt nào
giữa "người quản trị" và "ứng dụng agent".

---

## 2. Nội dung cần làm

### 2.1. Tạo user và gán role — PostgreSQL

```sql
-- Tạo user đăng nhập được (khác với role NOLOGIN ở bước 2)
CREATE USER nlsql_agent_qldt LOGIN PASSWORD '<mật khẩu mạnh>';

-- Gán role agent (đã tạo ở bước 2, đã cấp quyền ở bước 3) vào user
GRANT agent_qldt_ro TO nlsql_agent_qldt;

-- Giới hạn tài nguyên
ALTER ROLE nlsql_agent_qldt SET statement_timeout = '30s';
ALTER ROLE nlsql_agent_qldt SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE nlsql_agent_qldt CONNECTION LIMIT 20;
```

**Về `CONNECTION LIMIT 20`:** ứng dụng cấu hình `db_pool_size=5` +
`db_max_overflow=10` (`config.py:57-58`) → tối đa 15 kết nối. Đặt 20 là đủ dư,
đồng thời chặn trường hợp rò rỉ kết nối làm cạn `max_connections=100` của server.

**Về `statement_timeout`:** chặn câu truy vấn do LLM sinh ra chạy vô tận làm treo
DB. Lưu ý ứng dụng cũng có giới hạn riêng ở tầng pool nhưng không thay thế được
giới hạn phía DB.

### 2.2. Tạo user và gán role — ClickHouse

```sql
CREATE USER nlsql_agent_qldt
    IDENTIFIED WITH sha256_password BY '<mật khẩu mạnh>'
    SETTINGS max_execution_time = 30,
             max_memory_usage = 10000000000,
             readonly = 1;

GRANT agent_qldt_ro TO nlsql_agent_qldt;

-- BẮT BUỘC: ClickHouse không tự kích hoạt role sau khi gán
SET DEFAULT ROLE agent_qldt_ro TO nlsql_agent_qldt;
```

**Điểm khác biệt quan trọng so với Postgres:**

| | PostgreSQL | ClickHouse |
|---|---|---|
| Gán role xong có dùng được ngay | **Có** | **Không** — phải `SET DEFAULT ROLE` |
| Giới hạn thời gian chạy | `statement_timeout` | `max_execution_time` |
| Giới hạn bộ nhớ | Không trực tiếp | `max_memory_usage` |
| Chế độ chỉ đọc cấp setting | Không có | `readonly = 1` |

Quên `SET DEFAULT ROLE` là lỗi thường gặp — user đăng nhập được nhưng không có
quyền gì, báo lỗi khó hiểu.

`readonly = 1` là lớp chặn **thứ hai**, độc lập với `GRANT`. Kể cả nếu `GRANT` bị
cấu hình sai, setting này vẫn chặn mọi lệnh ghi.

### 2.3. Nếu tách theo domain

Lặp lại cho `tcns`:

```sql
CREATE USER nlsql_agent_tcns LOGIN PASSWORD '<mật khẩu khác>';
GRANT agent_tcns_ro TO nlsql_agent_tcns;
```

**Vì sao nên tách 2 user thay vì 1 user dùng chung:**
Hiện `/qldt/chat` và `/tcns/chat` đều public, không authentication — ai gọi được
cái này thì gọi được cái kia bằng cách đổi URL. Nếu dùng chung một user có quyền
cả hai database thì việc tách role ở bước 2 mất tác dụng.

> **Lưu ý:** `tcns` hiện có **0 bảng**. Cần xác nhận domain này đã dùng chưa trước
> khi tạo user cho nó.

---

## 3. Các điểm cần lưu ý

### 3.1. Tạo user MỚI, không hạ quyền `ript`

**Khuyến nghị: tuyệt đối không chạy `ALTER ROLE ript NOSUPERUSER`.**

| | Tạo user mới | Hạ quyền `ript` |
|---|---|---|
| Ảnh hưởng hệ thống khác | **Không** | **Có thể làm gãy** |
| Rollback | Đổi lại `.env` | Phức tạp |
| Rủi ro | Thấp | Cao |

`ript` là tài khoản đăng nhập **duy nhất** của DB này, và server còn 2 database
khác (`ript`, `vbcc`). Nhiều khả năng có hệ thống khác đang dùng nó. Hạ quyền có
thể làm gãy thứ không liên quan tới agent.

### 3.2. Quản lý mật khẩu

Mật khẩu user mới sẽ nằm trong `.env`. Cần lưu ý:

- `.env` đã có trong `.gitignore` — **nên kiểm tra `git log` xem đã từng commit chưa**
- `docker-compose.prod.yml` nạp `.env` qua `env_file` — cùng file với môi trường dev
- Đề xuất: tách `.env.prod` riêng, không dùng chung file với dev

### 3.3. SSL đang tắt

```
ssl = off
```

Mật khẩu và dữ liệu truyền giữa ứng dụng và DB **không được mã hoá**. Code cũng
đang chủ động tắt: `config.py:132` dùng `?ssl=disable`, `config.py:155` dùng
`?sslmode=disable`.

Đây là vấn đề nằm ngoài phạm vi bước 4, nhưng cần nêu: nếu ứng dụng và DB không
cùng một máy/mạng tin cậy thì mật khẩu user mới cũng bị lộ trên đường truyền y
như mật khẩu `ript` hiện nay. Việc tạo user riêng vẫn có giá trị (giới hạn quyền),
nhưng không giải quyết được vấn đề đường truyền.

---

## 4. Kiểm thử

### 4.1. Xác nhận user và role đã gán đúng

```sql
-- Kiểm tra user tồn tại và đăng nhập được
SELECT rolname, rolcanlogin, rolconnlimit, rolsuper
FROM pg_roles WHERE rolname = 'nlsql_agent_qldt';
-- Kỳ vọng: rolcanlogin=t, rolconnlimit=20, rolsuper=f

-- Kiểm tra role đã gán vào user
SELECT r.rolname AS role_duoc_gan
FROM pg_auth_members m
JOIN pg_roles r ON r.oid = m.roleid
JOIN pg_roles u ON u.oid = m.member
WHERE u.rolname = 'nlsql_agent_qldt';
-- Kỳ vọng: agent_qldt_ro
```

ClickHouse:

```sql
SHOW GRANTS FOR nlsql_agent_qldt;
-- Kỳ vọng: GRANT agent_qldt_ro TO nlsql_agent_qldt
```

### 4.2. Đăng nhập bằng user mới và kiểm tra quyền

| Câu lệnh | Kỳ vọng |
|---|---|
| Đăng nhập bằng `nlsql_agent_qldt` | **Thành công** |
| `SELECT COUNT(*) FROM "SinhVien";` | **Thành công** |
| `SELECT current_user;` | `nlsql_agent_qldt` |
| `CREATE TABLE test_x (id int);` | **permission denied** |
| `UPDATE "SinhVien" SET hoTen='x';` | **permission denied** |
| `DROP TABLE "SinhVien";` | **must be owner** |
| `SELECT * FROM pg_authid;` | **permission denied** |
| `CREATE USER hacker ...;` | **permission denied** |

Hai dòng cuối xác nhận user mới không còn đặc quyền của superuser.

### 4.3. Kiểm tra giới hạn tài nguyên

```sql
-- Xác nhận statement_timeout có hiệu lực
SELECT pg_sleep(35);
-- Kỳ vọng: bị huỷ sau 30 giây với lỗi "canceling statement due to statement timeout"
```

---

## 5. Bảng tổng hợp

| # | Việc | Người làm | Công sức |
|---|---|---|---|
| 4.1 | `CREATE USER` + `GRANT role` (Postgres) | Anh chạy SQL | 15 phút |
| 4.2 | Đặt `statement_timeout`, `CONNECTION LIMIT` | Anh chạy SQL | 5 phút |
| 4.3 | `CREATE USER` + `SET DEFAULT ROLE` (ClickHouse) | Anh chạy SQL | 15 phút |
| 4.4 | Tạo user cho `tcns` (nếu dùng) | Anh chạy SQL | 10 phút |
| 4.5 | Kiểm thử | Anh + tôi | 30 phút |

**Tổng: khoảng 1–1,5 giờ.**

### Rủi ro

| | |
|---|---|
| Có sửa bảng/dữ liệu không | **Không** |
| Có ảnh hưởng `ript` không | **Không** — tạo tài khoản mới hoàn toàn |
| Có ảnh hưởng hệ thống khác không | **Không** |
| Rollback | Đổi lại `.env` về `ript`, hoặc `DROP USER nlsql_agent_qldt` |

**Sau bước 4, ứng dụng vẫn chưa dùng user mới** — vẫn chạy bằng `ript` cho tới
khi làm bước 5 (đổi `.env`). Nghĩa là bước 4 có thể làm trước, kiểm thử kỹ, rồi
mới chuyển đổi khi sẵn sàng. Không có thời điểm nào hệ thống bị gián đoạn.

---

## 6. Quan hệ với các bước khác

```
Bước 2 (CREATE ROLE)  →  Bước 3 (GRANT quyền cho role)
                                    ↓
                         Bước 4 (CREATE USER + gán role)   ← tài liệu này
                                    ↓
                         Bước 5 (app đổi sang user mới)
```

**Bước 4 phụ thuộc bước 2 và 3** — phải có role và role phải có quyền trước.
Nếu gán một role chưa được `GRANT` gì thì user tạo ra sẽ không đọc được bảng nào.

**Bước 4 không có tác dụng nếu thiếu bước 5** — user tồn tại nhưng ứng dụng vẫn
kết nối bằng `ript`.

---

## 7. Mức đáp ứng sau khi hoàn thành

| | Trước | Sau bước 4 |
|---|---|---|
| Bước 4 riêng | 0% | **100%** |
| *Toàn bộ 5 bước* | *~8%* | *~45%* (chưa tính bước 5) |

**Giải quyết được:**
- Có tài khoản riêng cho agent, tách khỏi tài khoản quản trị
- Giới hạn được số kết nối và thời gian chạy truy vấn
- Có thể thu hồi quyền agent mà không ảnh hưởng `ript`

**Chưa giải quyết:**
- Ứng dụng vẫn dùng `ript` cho tới khi làm bước 5
- SSL vẫn tắt — mật khẩu truyền không mã hoá
- 64 cột nhạy cảm vẫn đọc được (cần bước 1)

---

## Phụ lục — Nguồn số liệu

Đo trực tiếp ngày 11/09/2026:

| Số liệu | Cách lấy |
|---|---|
| 1 login role `ript`, connlimit=-1 | `SELECT rolname,rolconnlimit,rolvaliduntil FROM pg_roles WHERE rolcanlogin` |
| `password_encryption=scram-sha-256` | `SHOW password_encryption` |
| `ssl=off` | `SHOW ssl` |
| `max_connections=100` | `SHOW max_connections` |
| `server_version=15.14` | `SHOW server_version` |
| ClickHouse 1 user, 0 role | `SHOW USERS` / `SHOW ROLES` |

**File liên quan:**
- `config.py:57-58` — `db_pool_size=5`, `db_max_overflow=10`
- `config.py:132,141,155` — chuỗi kết nối đang tắt SSL
- `db/connection.py:118` — khởi tạo engine với pool
- `.env` — nơi đổi user/password ở bước 5
