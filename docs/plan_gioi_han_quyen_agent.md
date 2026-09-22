# Plan: Giới hạn quyền đọc/ghi + phạm vi dữ liệu cho AI Agent

> Trạng thái: **BẢN PLAN — chưa chạy DDL, chưa sửa code.**
> Ngày khảo sát: 2026-09-08. Máy đích: `192.168.30.28:18123` (ClickHouse 26.6.2.81).

## 0. Hiện trạng khảo sát được (đọc kỹ phần này trước khi làm)

| Hạng mục | Thực tế |
|---|---|
| DB đang active | **ClickHouse** (`ACTIVE_DB=clickhouse`), KHÔNG phải PostgreSQL |
| Host | `192.168.30.28:18123` (HTTP), native `19000` |
| Database tồn tại | Chỉ **`qldt`** (253 bảng, 0 view). **`tcns` KHÔNG tồn tại** |
| User agent đang dùng | `clickhouse` — quyền gần-admin |
| Quyền của user đó | `SELECT, INSERT, ALTER, CREATE, DROP, TRUNCATE, OPTIMIZE, KILL QUERY, CREATE USER, DROP USER, CREATE ROLE, ... ON *.* WITH GRANT OPTION` |
| Access storage | `users_xml` (precedence 1) + **`local_directory` (precedence 2) → đã bật SQL-driven access** |
| Roles / profiles hiện có | roles: *(không có)*; profiles: `default`, `readonly`; quotas: `default` |
| Qdrant index | `schema_collection_qldt` = **253 điểm**, `schema_collection_tcns` = 161 điểm |

### Vì sao cú pháp trong yêu cầu cần dịch lại

Yêu cầu ban đầu viết theo PostgreSQL. ClickHouse không có các khái niệm đó:

| Yêu cầu (PostgreSQL) | Tương đương ClickHouse |
|---|---|
| `CREATE ROLE agent NOLOGIN` | `CREATE ROLE agent` (role trong CH vốn không đăng nhập được → `NOLOGIN` là mặc định, không có từ khoá này) |
| `GRANT USAGE ON SCHEMA x TO agent` | Không có schema. Cấp theo `database.table`: `GRANT SELECT ON qldt.<table>` |
| `GRANT SELECT/CREATE ON <bảng>` | `GRANT SELECT ON qldt.<table> TO agent` (tuyệt đối **không** cấp CREATE cho agent) |
| `CREATE USER ... ; GRANT agent TO user` | `CREATE USER agent_ro IDENTIFIED WITH sha256_password BY '...'` + `GRANT agent TO agent_ro` |
| `statement_timeout`, `default_transaction_read_only` | SETTINGS PROFILE: `readonly=1`, `max_execution_time`, `max_result_rows`, `max_memory_usage` |
| Row-Level Security (RLS policy) | `CREATE ROW POLICY` |

ClickHouse còn cho 2 lớp bảo vệ mà Postgres không có sẵn tương đương trực tiếp, nên plan sẽ dùng:
- **SETTINGS PROFILE `readonly=1`** — chặn mọi DDL/DML ở tầng engine, kể cả khi grant bị cấu hình sai.
- **QUOTA** — giới hạn số query/lượng row đọc theo giờ, chống agent loop vô hạn đốt tài nguyên.

### Hai lỗ hổng trong code hiện tại mà plan này phải bịt

1. **`agents/executor_agent.py:71`** — SQL ghi chỉ bị chặn khi `app_env != "development"`:
   ```python
   if settings.app_env != "development" and _DANGEROUS_PATTERN.search(final_sql):
   ```
   `.env` đang là `APP_ENV=development` → **hiện tại agent được phép chạy `DROP`/`DELETE`/`TRUNCATE`** trên DB thật, chỉ cần LLM sinh ra câu đó. Đây chính là lý do phải siết ở tầng DB thay vì tin vào regex.

2. **Regex là lớp phòng thủ yếu.** `_DANGEROUS_PATTERN` (`executor_agent.py:21`, `sql_check_agent.py:26`) match theo từ khoá, dễ vượt bằng comment lồng, chuỗi nối, hoặc `INSERT` trong tên cột. Regex nên giữ làm lớp fail-fast, nhưng **không được là lớp duy nhất**.

Ngoài ra có 1 bug cấu hình phát hiện kèm:

3. **`.env:11-13`** — `CH_DB_NAME_TCNS` bị khai báo **2 lần**, và thiếu `CH_DB_NAME_QLDT`:
   ```
   CH_DB_NAME=warehouse        # config.py không hề đọc biến này
   CH_DB_NAME_TCNS=qldt        # bị ghi đè bởi dòng dưới
   CH_DB_NAME_TCNS=tcns
   ```
   `config.py:24-25` chỉ đọc `ch_db_name_qldt` / `ch_db_name_tcns`. Kết quả: domain `qldt` rơi về default `"qldt"` (may mắn đúng), domain `tcns` trỏ tới database **không tồn tại**.

---

## 1. Bước 1 — Danh sách bảng cho agent

### 1.1 Kết quả phân loại 253 bảng

Giao 3 tiêu chí: (a) có trong `QLDT_FINAL.xlsx` sheet `Database Schema` (228 bảng nghiệp vụ đã được mô tả tiếng Việt), (b) `total_rows > 0`, (c) không thuộc nhóm hệ thống/PII.

- **111 bảng** = nghiệp vụ + có dữ liệu → ứng viên whitelist.
- **15 bảng** có dữ liệu nhưng ngoài Excel → nhóm hệ thống, **loại**:
  `User`, `File`, `ImportSession`, `Increment`, `HamSinhMa`, `QuyTac`, `QuyTacMa`, `ToaNha`,
  `DangKyNghiHoc`, `DangKySachEd`, `DotDangKyEd`, `DotDangKyEdHocLieu`,
  `DotDangKyEdKhoaSinhVien`, `DotDangKyEdTaiKhoan`, `QuanLyLALVKL`
- Còn lại: bảng rỗng (0 row) → không cấp, giảm nhiễu cho agent.

### 1.2 Danh sách LOẠI TRỪ tuyệt đối (chứa credential / PII)

Khảo sát `system.columns` tìm cột nhạy cảm:

| Bảng | Cột nhạy cảm | Xử lý |
|---|---|---|
| `User` | **`password`**, `email` | **KHÔNG cấp** |
| `Auth` | toàn bộ | **KHÔNG cấp** |
| `DataPartition`, `DataPartitionUser` | `userEmail` — bảng phân quyền dữ liệu | **KHÔNG cấp** |
| `OneSignalUser`, `Notification`, `UserTopic`, `Topic` | định danh thiết bị/push | **KHÔNG cấp** |
| `DotDangKyEdTaiKhoan`, `LoaiTaiKhoanEd` | `maTaiKhoan`, `tenTaiKhoan` | **KHÔNG cấp** |
| `SinhVien` | **113 cột, ~45 cột nhạy cảm** — xem bảng phân loại 1.2b | **Cấp qua VIEW che cột** (mục 1.3) |
| `PhuHuynh` | `email`, `soDienThoai` | Cấp qua view hoặc loại |
| `NguoiHuongDan`, `HoiDongHocVu`, `ThanhVienHoiDong`, `ThanhVienThamDu`, `DeCuongGv`, `QuanLyLALVKL`, `PhieuDkCtdt`, `DangKyMoNganh`, `DonDangKyChuyenNganh`, `CoSoDaoTao` | `email`, `soDienThoai` | Cấp qua view che cột |

### 1.2b Phân loại 113 cột của `SinhVien` (bảng trung tâm)

`SinhVien` là bảng agent buộc phải dùng nhưng chứa lượng PII lớn hơn dự kiến. Rà `system.columns` cho kết quả:

**Nhóm PHẢI che — định danh & tài chính**
`cccd`, `noiCapCccd`, `ngayCapCccd`, `soTaiKhoanNganHang`, `tenNganHang`, `chiNhanhNganHang`,
`soBaoHiemSinhVien`, `maBenhVienKhamChuaBenh`, `ssoId`, `entraId`, `faceRegImgUrl`, `needUpdateFaceReg`

**Nhóm PHẢI che — liên hệ**
`soDienThoai`, `soDienThoai2`, `email`, `email2`, `nguoiLienLac`, `soDienThoaiNguoiLienLac`,
`thanhVienGiaDinh`, `thongTinAnhChiEm`, `thongTinCacCon`, `anhDaiDienUrl`

**Nhóm PHẢI che — dữ liệu đặc biệt (sức khoẻ, tôn giáo, chính trị)**
`ghiChuYTe`, `canNang`, `chieuCao`, `loaiKhuyetTat`, `maLoaiKhuyetTat`, `tonGiao`, `danToc`,
`laDangVien`, `ngayVaoDang`, `ngayVaoDangChinhThuc`, `daHocLopCamTinhDang`, `laDoanVien`, `ngayVaoDoan`

Đây là nhóm dữ liệu nhạy cảm nhất — dữ liệu sức khoẻ và quan điểm chính trị/tôn giáo. Agent phân tích học vụ không có lý do nghiệp vụ nào cần đọc, nên che tuyệt đối.

**Nhóm PHẢI che — địa chỉ chi tiết**
`soNhaTenDuongQueQuan`, `soNhaTenDuongThuongTru`, `xaPhuongNoiSinh`, `xaPhuongQueQuan`,
`xaPhuongThuongTru`, `hoKhauThuongTru`, `hoKhauThuongTruOld`, `queQuanOld`
(giữ `tinhTpQueQuan`, `tinhTpThuongTru` ở mức tỉnh/thành — đủ cho thống kê theo vùng, không định danh được cá nhân)

**Nhóm NÊN che — audit nội bộ, vô nghĩa với agent**
`createdById`, `createdByUsername`, `updatedById`, `updatedByUsername`,
`deletedById`, `deletedByUsername`, `dataPartitionCode`, `choPhepSua`,
`trangThaiHocOld`, `trangThaiHocNganh1Old`, `trangThaiHocNganh2Old`

**Nhóm GIỮ LẠI — agent cần để trả lời học vụ**
`_id`, `ma`, `ten`, `firstName`, `lastName`, `middleName`, `ngaySinh`, `gioiTinh`, `quocTich`,
`maNganh`, `maNganh2`, `maChuyenNganh`, `maChuyenNganh2`, `maKhoaNganh`, `maKhoaNganh2`,
`maKhoaSinhVien`, `maKhoaSinhVien2`, `namNhapHoc`, `ngayNhapHoc`, `namTotNghiep`,
`trangThaiHoc`, `trangThaiHocNganh1`, `trangThaiHocNganh2`, `maTrinhDo`, `maHinhThuc`, `maCSDT`,
`diemTrungTuyen`, `doiTuongDauVao`, `doiTuong`, `khuVucUuTienTuyenSinh`, `doiTuongUuTienTuyenSinh`,
`xepLoaiHocTapTHPT`, `xepLoaiHanhKiemTHPT`, `ketQuaTuyenSinh`,
`tinhTpNoiSinh`, `tinhTpQueQuan`, `tinhTpThuongTru`, `createdAt`, `updatedAt`

Vì danh sách che (~45 cột) dài hơn danh sách giữ (~38 cột) không đáng kể, và mặc định an toàn quan trọng hơn tiện lợi, **đề xuất dùng whitelist cột tường minh** (`SELECT <38 cột>`) thay vì `EXCEPT`. Lý do: khi bảng thêm cột PII mới, `EXCEPT` sẽ **tự động phơi ra** cột đó, còn whitelist thì không.

### 1.3 View nghiệp vụ cần tạo

ClickHouse hiện có **0 view**. Vì `SinhVien` (51k row) là bảng trung tâm mà agent buộc phải dùng, nhưng lại chứa CCCD + số tài khoản ngân hàng, giải pháp: **không grant bảng gốc, chỉ grant view đã che cột**.

```sql
CREATE DATABASE IF NOT EXISTS qldt_agent;

-- View sinh viên: whitelist cột tường minh (an toàn khi bảng thêm cột mới)
CREATE OR REPLACE VIEW qldt_agent.v_sinh_vien
DEFINER = clickhouse SQL SECURITY DEFINER
AS SELECT
    _id, ma, ten, firstName, middleName, lastName, ngaySinh, gioiTinh, quocTich,
    maNganh, maNganh2, maChuyenNganh, maChuyenNganh2, maKhoaNganh, maKhoaNganh2,
    maKhoaSinhVien, maKhoaSinhVien2, namNhapHoc, ngayNhapHoc, namTotNghiep,
    trangThaiHoc, trangThaiHocNganh1, trangThaiHocNganh2, maTrinhDo, maHinhThuc, maCSDT,
    diemTrungTuyen, doiTuongDauVao, doiTuong, khuVucUuTienTuyenSinh, doiTuongUuTienTuyenSinh,
    xepLoaiHocTapTHPT, xepLoaiHanhKiemTHPT, ketQuaTuyenSinh,
    tinhTpNoiSinh, tinhTpQueQuan, tinhTpThuongTru, createdAt, updatedAt
FROM qldt.SinhVien;

-- Ví dụ view che liên hệ giảng viên
CREATE OR REPLACE VIEW qldt_agent.v_de_cuong_gv AS
SELECT * EXCEPT (soDienThoai) FROM qldt.DeCuongGv;
```

Lưu ý kỹ thuật ClickHouse:
- `SELECT * EXCEPT (...)` **đã kiểm chứng chạy được** trên CH 26.6 của hệ thống này. Tuy nhiên xem 1.2b: whitelist cột tường minh an toàn hơn `EXCEPT` vì cột PII thêm mới sẽ không bị tự động phơi ra.
- View thường (không MATERIALIZED) không tốn storage, luôn đọc dữ liệu mới.
- **Cần `SQL SECURITY`**: từ CH 24.4+, view mặc định `SQL SECURITY INVOKER` — người gọi vẫn phải có quyền trên bảng gốc, làm view che cột trở nên vô nghĩa. Phải đặt `DEFINER`:
  ```sql
  CREATE OR REPLACE VIEW qldt_agent.v_sinh_vien
  DEFINER = clickhouse SQL SECURITY DEFINER
  AS SELECT * EXCEPT (cccd, ...) FROM qldt.SinhVien;
  ```
  Khi đó cấp `SELECT ON qldt_agent.v_sinh_vien` cho agent mà **không** cấp `SELECT ON qldt.SinhVien`.

### 1.4 Việc cần làm ở bước 1

- [ ] Chốt whitelist cuối từ 111 bảng ứng viên (đề xuất: giữ cả 111, trừ nhóm 1.2).
- [ ] Rà cột PII trên từng bảng whitelist, quyết bảng nào cần view.
- [ ] Viết `scripts/agent_views.sql` tạo database `qldt_agent` + các view `DEFINER`.
- [ ] Ghi whitelist thành file cấu hình dùng chung cho cả DDL và Qdrant (mục 6).

---

## 2. Bước 2 — Tạo role

```sql
-- Role đọc dữ liệu nghiệp vụ
CREATE ROLE IF NOT EXISTS agent;
```

ClickHouse không có `NOLOGIN`: role không phải principal đăng nhập được, nên tính chất "no login" là mặc định.

Kèm theo, tạo **settings profile** — đây là lớp chặn ghi thật sự, mạnh hơn regex:

```sql
CREATE SETTINGS PROFILE IF NOT EXISTS agent_profile SETTINGS
    readonly = 1,                      -- chặn mọi INSERT/ALTER/DROP/TRUNCATE ở tầng engine
    max_execution_time = 30,           -- khớp statement_timeout=30000 đang dùng cho Postgres
    max_result_rows = 1000,            -- khớp MAX_ROWS trong executor_agent.py
    max_result_bytes = 100000000,
    result_overflow_mode = 'break',
    max_memory_usage = 4000000000,
    max_rows_to_read = 50000000,       -- chặn full-scan DiemDanh (856k row) kiểu tích Descartes
    read_overflow_mode = 'throw',
    max_bytes_before_external_group_by = 2000000000,
    allow_ddl = 0;                     -- chặn DDL kể cả khi grant sai
```

Về `readonly`: `readonly=1` cấm cả việc client tự đổi setting; `readonly=2` cho phép đổi setting nhưng vẫn cấm ghi. Chọn **`readonly=1`** để agent không tự nâng `max_execution_time`. Cần kiểm tra `pool_pre_ping` và `connect_args` của SQLAlchemy không cố set session setting nào — nếu có sẽ lỗi, khi đó dùng `readonly=2` + quota bù.

Và **quota** chống loop vô hạn (agent có retry loop trong `graph/builder.py`):

```sql
CREATE QUOTA IF NOT EXISTS agent_quota
    KEYED BY user_name
    FOR INTERVAL 1 HOUR MAX queries = 1000, errors = 200, result_rows = 1000000, read_rows = 500000000, execution_time = 3600
    TO agent;
```

### Việc cần làm
- [ ] Viết `scripts/agent_role.sql` gồm `CREATE ROLE` + `SETTINGS PROFILE` + `QUOTA`.
- [ ] Xác nhận `readonly=1` không phá SQLAlchemy/asynch driver (test trên user tạm trước).

---

## 3. Bước 3 — Cấp quyền đọc bảng/view

**Nguyên tắc: chỉ `SELECT`. Không `CREATE`, không `INSERT`, không `ALTER`, không `DROP`.**
Yêu cầu ban đầu ghi `GRANT SELECT/CREATE/...` — với agent NL→SQL thì `CREATE` là không cần thiết và là rủi ro trực tiếp; plan này cố ý loại bỏ.

```sql
-- 3.1 Quyền đọc metadata (agent cần để introspect schema)
GRANT SHOW TABLES, SHOW COLUMNS ON qldt.* TO agent;
GRANT SELECT ON information_schema.* TO agent;
-- KHÔNG cấp SELECT ON system.* (chứa system.users, query_log → rò rỉ thông tin)
-- Nếu schema_agent cần system.columns, cấp riêng đúng 2 bảng:
GRANT SELECT ON system.columns TO agent;
GRANT SELECT ON system.tables  TO agent;

-- 3.2 Quyền đọc view đã che PII
GRANT SELECT ON qldt_agent.* TO agent;

-- 3.3 Quyền đọc từng bảng whitelist (KHÔNG dùng qldt.*)
GRANT SELECT ON qldt.DiemDanh TO agent;
GRANT SELECT ON qldt.LopHocPhanSinhVien TO agent;
GRANT SELECT ON qldt.DiemHocPhan TO agent;
GRANT SELECT ON qldt.KqhtTichLuy TO agent;
GRANT SELECT ON qldt.KqhtHocKy TO agent;
GRANT SELECT ON qldt.DmNganh TO agent;
GRANT SELECT ON qldt.Nganh TO agent;
GRANT SELECT ON qldt.KhoaNganh TO agent;
GRANT SELECT ON qldt.HocPhan TO agent;
GRANT SELECT ON qldt.LopHocPhan TO agent;
-- ... (sinh tự động từ file whitelist, xem mục 3.4)

-- 3.4 Gán profile cho role
ALTER ROLE agent SETTINGS PROFILE 'agent_profile';
```

**Cấp quyền theo cột (thay cho view)** — ClickHouse hỗ trợ column-level grant, là lựa chọn thứ 2 nếu không muốn quản view:
```sql
GRANT SELECT(id, maSinhVien, hoTen, ngaySinh, maNganh, maLopHanhChinh, trangThai)
    ON qldt.SinhVien TO agent;
```
Cách này gọn hơn view nhưng phải liệt kê tay cột cho phép, và mỗi lần bảng thêm cột thì cột mới **không** tự được cấp (an toàn hơn về mặc định). Đề xuất: **dùng view cho `SinhVien`** (nhiều cột, agent cần linh hoạt), **dùng column-grant cho các bảng chỉ có 1-2 cột PII**.

### Việc cần làm
- [ ] Viết script sinh `GRANT` từ file whitelist (tránh gõ tay 111 dòng).
- [ ] Quyết định view vs column-grant cho từng bảng có PII.
- [ ] Xác nhận `schema_agent` cần chính xác bảng `system.*` nào — hiện `_CH_GET_COLUMNS` dùng `system.columns`, `_CH_GET_TABLES` dùng `SHOW TABLES`.

---

## 4. Bước 4 — Tạo user DB và gán role

```sql
CREATE USER IF NOT EXISTS agent_ro
    IDENTIFIED WITH sha256_password BY '<sinh-bang-openssl-rand>'
    HOST IP '<ip-app-server>/32'          -- giới hạn nguồn kết nối
    DEFAULT ROLE agent
    SETTINGS PROFILE 'agent_profile';

GRANT agent TO agent_ro;

-- Chốt: user không được tự nâng quyền
ALTER USER agent_ro DEFAULT ROLE agent;   -- không có ADMIN OPTION
```

Điểm cần chú ý:
- `DEFAULT ROLE agent` để role tự active mỗi phiên; nếu thiếu, kết nối lên sẽ không có quyền nào cho tới khi `SET ROLE`.
- `HOST IP` giới hạn user chỉ dùng được từ app server — chặn trường hợp credential lọt ra ngoài.
- Sinh password: `openssl rand -base64 32`.
- **KHÔNG** dùng `WITH GRANT OPTION`, **KHÔNG** `ACCESS MANAGEMENT`.

### Việc cần làm
- [ ] Sinh password mạnh, lưu vào secret store (không commit).
- [ ] Xác định IP app server để đặt `HOST IP`.
- [ ] Viết `scripts/agent_user.sql` (password truyền qua biến, không hardcode).

---

## 5. Bước 5 — Chỉ cho agent truy cập qua user `agent_ro`

Đây là phần **sửa code**, gồm 4 việc.

### 5.1 Thêm biến cấu hình riêng cho agent

`.env.example` + `.env`:
```env
# Read-only credential dành riêng cho AI Agent
CH_AGENT_USER=agent_ro
CH_AGENT_PASSWORD=
PG_AGENT_USER=agent_ro
PG_AGENT_PASSWORD=
```

`config.py` — thêm field + URL builder riêng:
```python
ch_agent_user: str = ""
ch_agent_password: str = ""
pg_agent_user: str = ""
pg_agent_password: str = ""

@property
def agent_db_user(self) -> str:
    u = self.ch_agent_user if self.active_db == "clickhouse" else self.pg_agent_user
    return u or self.db_user          # fallback, nhưng phải log WARNING

def get_agent_database_url(self, domain: str = "qldt") -> str:
    ...  # giống get_database_url nhưng dùng agent_db_user/password
```

### 5.2 Tách engine: engine admin vs engine agent

`db/connection.py` hiện tạo **một** engine per domain dùng `settings.db_user` (mục 246-263 cho Postgres, 215-221 cho ClickHouse). Cần tách:

- `engines[domain]` — giữ nguyên, dùng cho tác vụ hệ thống (migration, index schema).
- `agent_engines[domain]` — **mới**, dùng credential `agent_ro`.
- Thêm `get_agent_db_context(domain)` và `agent_ch_execute(domain, sql)`.

### 5.3 Chuyển các agent node sang engine agent

| File | Hàm | Đổi thành |
|---|---|---|
| `agents/executor_agent.py:47` | `get_db_context(domain)` | `get_agent_db_context(domain)` |
| `agents/executor_agent.py:38` | `ch_execute(domain, sql)` | `agent_ch_execute(domain, sql)` |
| `agents/executor_agent.py:131` | `EXPLAIN ANALYZE` | engine agent (chỉ đọc, OK) |
| `agents/sql_check_agent.py:74,78` | `EXPLAIN` dry-run | engine agent — **quan trọng**: EXPLAIN phải chạy bằng đúng quyền agent, nếu không sẽ pass ở check rồi fail ở execute |
| `agents/schema_agent.py:115,122` | introspect schema | engine agent (để schema thấy đúng tập bảng agent được phép) |
| `scripts/index_schema.py` | indexing | **giữ engine admin** hoặc dùng agent engine — xem 6.1 |

### 5.4 Siết lại lớp regex (không bỏ, nhưng sửa logic sai)

`agents/executor_agent.py:71` — bỏ điều kiện `app_env != "development"`:
```python
# TRƯỚC (sai): development bypass hoàn toàn
if settings.app_env != "development" and _DANGEROUS_PATTERN.search(final_sql):

# SAU: luôn chặn ở tầng app; tầng DB (readonly=1) là lớp thứ 2
if _DANGEROUS_PATTERN.search(final_sql):
```
Nếu dev thật sự cần chạy DDL, dùng biến riêng `ALLOW_WRITE_SQL=false` thay vì suy ra từ `app_env`.

### Việc cần làm
- [ ] `config.py`: thêm 4 field + `get_agent_database_url()`.
- [ ] `db/connection.py`: thêm `agent_engines`, `get_agent_db_context()`, `agent_ch_execute()`.
- [ ] Sửa 3 agent file sang engine agent.
- [ ] Sửa logic bypass ở `executor_agent.py:71`.
- [ ] Log WARNING khi `CH_AGENT_USER` rỗng (đang fallback về user admin).

---

## 6. Bước 6 — Đồng bộ whitelist với Qdrant (bắt buộc, nếu bỏ sẽ vỡ)

Đây là hệ quả mà 5 bước gốc chưa nêu, nhưng **không làm thì agent sẽ lỗi liên tục**.

Vấn đề: `schema_collection_qldt` đang index đủ **253 bảng**. `schema_agent` chọn bảng bằng semantic search trên collection đó (`schema_agent.py:243`). Nếu DB chỉ cấp 111 bảng:

1. Người dùng hỏi → Qdrant trả về bảng `User` hoặc `Auth` (không được cấp).
2. `sql_gen_agent` sinh SQL trên bảng đó.
3. `sql_check_agent` chạy `EXPLAIN` → `ACCESS_DENIED`.
4. LLM correction loop chạy vô ích, tốn token, cuối cùng trả lỗi cho user.

### 6.1 Cách xử lý

- [ ] Re-index Qdrant **chỉ với bảng trong whitelist**. `scripts/index_schema.py:74` hiện gọi `_fetch_all_tables(domain)` → thêm filter theo whitelist.
- [ ] Lưu ý `index_schema.py:70-72`: nếu collection đã tồn tại thì **`continue` — bỏ qua indexing**. Muốn re-index phải xoá collection trước, hoặc thêm flag `--force`.
- [ ] Nguồn whitelist duy nhất: 1 file (vd `config/agent_tables.yml`) dùng cho cả `GRANT`, cả Qdrant indexing, cả `TABLE_RULES`.
- [ ] Nếu dùng view `qldt_agent.v_sinh_vien`: index tên view thay tên bảng, và cập nhật `TABLE_RULES` trong `config.py:87` (đang ghi `"SinhVien"`) cho khớp — nếu không LLM vẫn sinh `FROM SinhVien`.

### 6.2 Xử lý domain `tcns`

`tcns` không tồn tại trên ClickHouse nhưng `db/connection.py:203` vẫn tạo engine cho nó, và Qdrant có 161 điểm. Cần chốt: xoá domain `tcns` khỏi code, hay tạo database `tcns` thật. Kèm sửa bug `.env:11-13` (mục 0).

---

## 7. Bước 7 — Kiểm thử

Tạo `test/test_agent_permissions.py` khẳng định các mệnh đề sau:

| # | Kiểm thử | Kỳ vọng |
|---|---|---|
| 1 | `SELECT count() FROM qldt.SinhVien` bằng `agent_ro` | ACCESS_DENIED (chỉ được dùng view) |
| 2 | `SELECT count() FROM qldt_agent.v_sinh_vien` | OK |
| 3 | `SELECT cccd FROM qldt_agent.v_sinh_vien` | Lỗi "no column cccd" |
| 3b | `SELECT ghiChuYTe FROM qldt_agent.v_sinh_vien` | Lỗi — dữ liệu sức khoẻ đã bị che |
| 3c | `SELECT laDangVien FROM qldt_agent.v_sinh_vien` | Lỗi — dữ liệu chính trị đã bị che |
| 3d | `SELECT soTaiKhoanNganHang FROM qldt_agent.v_sinh_vien` | Lỗi — dữ liệu tài chính đã bị che |
| 3e | `SELECT ssoId, entraId, faceRegImgUrl FROM qldt_agent.v_sinh_vien` | Lỗi — định danh/sinh trắc đã bị che |
| 4 | `SELECT * FROM qldt.User` | ACCESS_DENIED |
| 5 | `SELECT * FROM qldt.Auth` | ACCESS_DENIED |
| 6 | `INSERT INTO qldt.SinhVien VALUES (...)` | Lỗi readonly |
| 7 | `DROP TABLE qldt.SinhVien` | Lỗi readonly / allow_ddl=0 |
| 8 | `TRUNCATE TABLE qldt.DiemDanh` | Lỗi readonly |
| 9 | `CREATE TABLE qldt.x (...)` | Lỗi allow_ddl=0 |
| 10 | `SELECT * FROM system.users` | ACCESS_DENIED |
| 11 | `SET max_execution_time=600` | Lỗi (readonly=1) |
| 12 | Query cố ý chậm > 30s | Bị kill bởi `max_execution_time` |
| 13 | Query trả > 1000 row | Bị cắt bởi `max_result_rows` + `result_overflow_mode='break'` |
| 14 | Toàn bộ 111 bảng whitelist | `SELECT count()` thành công hết |
| 15 | Mỗi bảng Qdrant đang index | Đều nằm trong whitelist (chống lệch mục 6) |
| 16 | Kết nối `agent_ro` từ IP khác | Bị từ chối (`HOST IP`) |

---

## 8. Thứ tự thi hành đề xuất

| Giai đoạn | Việc | Rủi ro |
|---|---|---|
| **A** | Chốt whitelist + rà cột PII (mục 1) | Không — chỉ đọc |
| **B** | Viết 4 file SQL: `agent_role.sql`, `agent_views.sql`, `agent_grants.sql`, `agent_user.sql` | Không — chưa chạy |
| **C** | Sửa code: `config.py`, `db/connection.py`, 3 agent file, fix `.env` (mục 5) | Thấp — có fallback về user cũ |
| **D** | Chạy SQL lên DB, tạo role/user/view | **Trung bình** — xem cảnh báo dưới |
| **E** | Re-index Qdrant theo whitelist (mục 6) | Thấp — tốn phí embedding |
| **F** | Chạy test suite (mục 7) | Không |
| **G** | Đổi `.env` sang `agent_ro`, restart app | Thấp — rollback bằng đổi lại biến |

### Cảnh báo về giai đoạn D

`192.168.30.28` là **DB dùng chung trên mạng nội bộ**. User `clickhouse` có `WITH GRANT OPTION` và rất có thể đang được **hệ thống khác dùng chung**. Do đó:

- Plan này **chỉ tạo mới** role/user/view. **Tuyệt đối không `REVOKE` gì trên user `clickhouse`** — sẽ làm hỏng hệ thống khác.
- User `clickhouse` là `users_xml` → **không thể `ALTER` qua SQL** kể cả khi muốn. Muốn siết nó phải sửa `/etc/clickhouse-server/users.xml` và restart. **Ngoài phạm vi plan này.**
- Việc app này ngừng dùng `clickhouse` và chuyển sang `agent_ro` là đủ để đạt mục tiêu, không cần đụng vào user cũ.
- Nên xin xác nhận người quản trị `192.168.30.28` trước khi chạy D.

---

## 9. Tóm tắt deliverable

**File SQL mới**
- `scripts/sql/agent_role.sql` — role + settings profile + quota
- `scripts/sql/agent_views.sql` — database `qldt_agent` + view `DEFINER` che PII
- `scripts/sql/agent_grants.sql` — `GRANT SELECT` theo whitelist (sinh tự động)
- `scripts/sql/agent_user.sql` — `CREATE USER agent_ro` + gán role

**File cấu hình mới**
- `config/agent_tables.yml` — whitelist dùng chung cho GRANT + Qdrant

**File code sửa**
- `config.py` — 4 field agent credential + `get_agent_database_url()`
- `db/connection.py` — `agent_engines`, `get_agent_db_context()`, `agent_ch_execute()`
- `agents/executor_agent.py` — dùng engine agent; bỏ bypass `development` ở dòng 71
- `agents/sql_check_agent.py` — `EXPLAIN` bằng engine agent
- `agents/schema_agent.py` — introspect bằng engine agent
- `scripts/index_schema.py` — filter whitelist + flag `--force`
- `.env` / `.env.example` — thêm agent credential; **fix `CH_DB_NAME_TCNS` trùng lặp**

**File test mới**
- `test/test_agent_permissions.py` — 16 assertion ở mục 7
