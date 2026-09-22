# Bước 3 — Cấp quyền đọc bảng / view / schema cho role agent

> **Yêu cầu gốc (anh Dũng - CNS):**
> *"3. Cấp quyền ghi đọc bảng/ view/ schema:*
> *`GRANT USAGE ON SCHEMA {tên schema} TO agent;`*
> *`GRANT SELECT/ CREATE/... ON {bảng/ view} TO agent.`"*

**Ngày khảo sát:** 11/09/2026
**Phạm vi:** Chỉ bước 3. Bước 2/4/5 xem `BUOC2_5_ROLE_VA_PHAN_QUYEN_DB.md`, bước 1 xem `BUOC1_DANH_SACH_BANG_VA_VIEW.md`
**Trạng thái:** Chưa bắt đầu — 0%

---

## 1. Hiện trạng (đo thực tế)

### Cấu trúc PostgreSQL `192.168.30.28:16543`

```
Databases trên server : postgres, qldt, ript, vbcc
Schema trong qldt     : public          (chỉ 1 schema duy nhất)
Object trong public   : 221 BASE TABLE  (0 VIEW)
Sequences             : 1
```

### Bảng kiểm tra quyền

| Hạng mục | Hiện trạng |
|---|---|
| Số `GRANT` đã cấp cho role agent | **0** — chưa có role nào |
| Số VIEW trong `public` | **0** |
| Schema cần cấp `USAGE` | `public` (chỉ 1) |
| `PUBLIC` đã có `USAGE` trên `public` | **Có** (mặc định Postgres) |
| Agent đang truy cập bằng | `ript` — **superuser**, không qua GRANT nào |

**Mức đáp ứng bước 3: 0%.**

Agent không cần `GRANT` vì đang là superuser — vượt qua toàn bộ hệ thống kiểm tra
quyền của Postgres.

### Phát hiện đáng lưu ý: có 2 database khác trên cùng server

```
postgres, qldt, ript, vbcc
```

`ript` và `vbcc` là database khác, không liên quan tới nghiệp vụ agent.
Vì `ript` là superuser nên **agent hiện đọc được cả hai database này** nếu câu SQL
trỏ tới chúng. Sau khi cấp quyền đúng theo bước 3, agent sẽ bị giới hạn trong `qldt`.

---

## 2. Nội dung cần cấp quyền

### 2.1. Cấp quyền — PostgreSQL

```sql
-- (a) Quyền truy cập schema
GRANT USAGE ON SCHEMA public TO agent_qldt_ro;

-- (b) Quyền đọc toàn bộ bảng hiện có
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_qldt_ro;

-- (c) Bảng/view tạo mới SAU NÀY cũng tự có quyền đọc
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO agent_qldt_ro;
```

> Lưu ý: `ALTER DEFAULT PRIVILEGES` chỉ áp dụng cho object do **chính user chạy
> lệnh này** tạo ra sau đó. Nếu bảng mới do user khác tạo thì vẫn phải `GRANT` lại.

**Nếu làm bước 1 (tạo view che cột nhạy cảm)** — cấp quyền trên schema view thay vì
cấp thẳng bảng gốc:

```sql
GRANT USAGE ON SCHEMA agent_qldt TO agent_qldt_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA agent_qldt TO agent_qldt_ro;

-- KHÔNG cấp quyền trên bảng gốc chứa cột nhạy cảm
-- (view tự đọc được bảng gốc nhờ quyền của người tạo view)
```

### 2.2. Cấp quyền — ClickHouse

Cú pháp khác hẳn, phân quyền theo **database** chứ không theo schema:

```sql
GRANT SHOW TABLES, SELECT ON qldt.* TO agent_qldt_ro;
```

Nếu có view riêng:

```sql
GRANT SHOW TABLES, SELECT ON agent_qldt.* TO agent_qldt_ro;
```

---

## 3. Hai điểm cần quyết định

### 3.1. Có cấp `CREATE` không?

Yêu cầu gốc ghi *"GRANT SELECT/ CREATE/..."*.

**Đề xuất: CHỈ cấp `SELECT`, KHÔNG cấp `CREATE`.**

| | Cấp `SELECT` | Cấp thêm `CREATE` |
|---|---|---|
| Agent trả lời câu hỏi | Đủ | Đủ |
| Agent tạo được bảng/view trong DB sản xuất | Không | **Có** |
| Ý nghĩa của việc hạ quyền | Giữ nguyên | **Mất phần lớn** |

Agent chỉ đọc dữ liệu để trả lời — không có nghiệp vụ nào cần tạo object.
Nếu cấp `CREATE`, agent có thể tạo bảng rác trong DB sản xuất, và một câu SQL do
LLM sinh sai vẫn gây hậu quả.

Trường hợp duy nhất cần cân nhắc: nếu sau này agent cần tạo bảng tạm cho truy vấn
phức tạp. Khi đó nên cấp `CREATE` trên **một schema riêng** (`agent_temp`), không
phải trên `public`.

### 3.2. Có chạy `REVOKE ALL ON SCHEMA public FROM PUBLIC` không?

Postgres mặc định cấp `USAGE` trên schema `public` cho vai trò `PUBLIC`
(đã xác nhận: `has_schema_privilege('public','public','USAGE') = True`).

Nghĩa là **mọi user trong DB đều có sẵn quyền vào schema `public`**, kể cả user
mới tạo. Nếu muốn siết chặt:

```sql
REVOKE ALL ON SCHEMA public FROM PUBLIC;
```

> **CẢNH BÁO:** lệnh này ảnh hưởng **tất cả user khác** đang dùng DB, không riêng
> agent. Server này còn 2 database khác (`ript`, `vbcc`) và có thể có hệ thống khác
> đang kết nối.
>
> **Khuyến nghị: KHÔNG chạy** trừ khi đã xác nhận không hệ thống nào phụ thuộc.
> Việc tạo user read-only riêng (bước 2/4) đã đủ đạt mục tiêu bảo mật, mà không
> có rủi ro làm gãy hệ thống khác.

---

## 4. Kiểm thử sau khi cấp quyền

### 4.1. Kiểm tra quyền đã cấp đúng

```sql
-- Xem role có những quyền gì
SELECT grantee, table_schema, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'agent_qldt_ro'
LIMIT 20;

-- Đếm số bảng đã cấp (kỳ vọng: 221)
SELECT COUNT(DISTINCT table_name)
FROM information_schema.role_table_grants
WHERE grantee = 'agent_qldt_ro' AND privilege_type = 'SELECT';
```

### 4.2. Kiểm thử chức năng — đăng nhập bằng user agent

| Câu lệnh | Kỳ vọng |
|---|---|
| `SELECT COUNT(*) FROM "SinhVien";` | **Thành công** |
| `SELECT * FROM "Diem" LIMIT 5;` | **Thành công** |
| `CREATE TABLE test_x (id int);` | **permission denied** |
| `INSERT INTO "SinhVien" VALUES (...);` | **permission denied** |
| `UPDATE "SinhVien" SET hoTen='x';` | **permission denied** |
| `DROP TABLE "SinhVien";` | **must be owner** |
| `SELECT * FROM pg_authid;` | **permission denied** |
| `\c vbcc` rồi `SELECT ...` | **permission denied** |

Hai dòng cuối là điểm quan trọng: xác nhận agent không còn đọc được bảng hệ thống
và không sang được database khác.

### 4.3. Kiểm thử ở tầng ứng dụng

- Gọi `/api/v1/qldt/chat` với câu hỏi thường → vẫn trả lời đúng
- Kiểm tra `error.log` không có lỗi quyền bất thường
- Thử vài câu hỏi phức tạp có `JOIN` nhiều bảng

---

## 5. Bảng tổng hợp

| # | Việc | Người làm | Công sức |
|---|---|---|---|
| 3.1 | `GRANT USAGE` + `SELECT` (Postgres) | Anh chạy SQL | 15 phút |
| 3.2 | `ALTER DEFAULT PRIVILEGES` | Anh chạy SQL | 5 phút |
| 3.3 | `GRANT` (ClickHouse) | Anh chạy SQL | 15 phút |
| 3.4 | Quyết định: có cấp `CREATE` không | **Anh + anh Dũng** | — |
| 3.5 | Quyết định: có `REVOKE FROM PUBLIC` không | **Anh + anh Dũng** | — |
| 3.6 | Kiểm thử | Anh + tôi | 30 phút |

**Tổng: khoảng 1–1,5 giờ** (không tính thời gian quyết định).

### Rủi ro

| | |
|---|---|
| Có sửa bảng/dữ liệu không | **Không** — `GRANT` chỉ ghi vào catalog quyền |
| Có ảnh hưởng user khác không | **Không**, trừ khi chạy `REVOKE FROM PUBLIC` |
| Rollback | `REVOKE ... FROM agent_qldt_ro` — tức thì |

---

## 6. Quan hệ với các bước khác

Bước 3 **không đứng riêng được** — nó cấp quyền cho role tạo ở bước 2, và role
chỉ có tác dụng khi được gán vào user ở bước 4:

```
Bước 2 (CREATE ROLE)  →  Bước 3 (GRANT)  →  Bước 4 (CREATE USER + gán role)
                                                      ↓
                                          Bước 5 (app đổi sang user đó)
```

Làm bước 3 mà bỏ bước 4–5 thì **không có tác dụng gì** — agent vẫn dùng `ript`.

**Phụ thuộc bước 1:** nếu muốn cấp quyền trên **view** (che 64 cột nhạy cảm) thay
vì bảng gốc, phải làm bước 1 trước. Nếu chưa có view thì cấp thẳng 221 bảng —
vẫn chặn được lệnh ghi, nhưng cột nhạy cảm vẫn đọc được.

---

## 7. Mức đáp ứng sau khi hoàn thành

| | Trước | Sau bước 3 (kèm 2/4/5) |
|---|---|---|
| Bước 3 riêng | 0% | **~90%** |
| *Toàn bộ 5 bước* | *~8%* | *~55%* |

Chưa đạt 100% vì phần *"cấp quyền trên **view**"* phụ thuộc bước 1 — chưa có view
nào được tạo. Khi bước 1 xong và cấp quyền trên view thay vì bảng gốc thì đạt 100%.

**Giải quyết được:**
- Lệnh ghi bị DB chặn tuyệt đối (không phụ thuộc regex ở tầng ứng dụng)
- Agent không đọc được bảng hệ thống (`pg_authid`, `pg_shadow`)
- Agent không sang được database `ript`, `vbcc`

**Chưa giải quyết:**
- 64 cột nhạy cảm vẫn đọc được nếu cấp quyền thẳng trên bảng gốc (cần bước 1)

---

## Phụ lục — Nguồn số liệu

Đo trực tiếp ngày 11/09/2026:

| Số liệu | Cách lấy |
|---|---|
| 4 database: `postgres, qldt, ript, vbcc` | `SELECT datname FROM pg_database WHERE datistemplate=false` |
| Schema trong `qldt`: chỉ `public` | `SELECT nspname FROM pg_namespace` |
| 221 BASE TABLE, 0 VIEW | `information_schema.tables GROUP BY table_type` |
| 1 sequence | `information_schema.sequences` |
| `PUBLIC` có `USAGE` trên `public` | `has_schema_privilege('public','public','USAGE')` |

**File liên quan:**
- `config.py:16-33` — khai báo kết nối DB
- `.env` — user/password hiện tại (`PG_DB_USER=ript`)
