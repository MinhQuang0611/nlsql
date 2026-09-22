# Bước 1 — Lên danh sách bảng / Tạo view nghiệp vụ cho Agent

> **Yêu cầu gốc (anh Dũng - CNS):**
> *"1. Lên danh sách các bảng / Tạo view theo nghiệp vụ nếu cần phục vụ cho agent"*

**Ngày khảo sát:** 11/09/2026
**Phạm vi tài liệu:** CHỈ bước 1 trong 5 bước. Không bao gồm bước 2–5 (role, grant, user).
**Trạng thái:** Chưa bắt đầu — tài liệu này mô tả các việc cần làm để hoàn thành.

---

## 1. Hiện trạng (số liệu đo thực tế)

Đã kết nối trực tiếp vào DB để đo, không phải ước lượng.

| Chỉ số | Giá trị | Nguồn |
|---|---|---|
| Bảng trong ClickHouse `qldt` | **253** | `SHOW TABLES FROM qldt` |
| Bảng có metadata mô tả | **228** | `QLDT_FINAL.xlsx` |
| Khớp giữa hai nguồn | **196** | So khớp tên |
| **Bảng có trong DB nhưng KHÔNG có metadata** | **57** | Chênh lệch |
| Tổng số cột | **3.075** | Excel |
| Cột nhạy cảm (ước tính sơ bộ) | **64** (2,1%) | Quét từ khóa |
| Bảng chứa cột nhạy cảm | **25 / 228** (11%) | Quét từ khóa |
| Bảng trong ClickHouse `tcns` | **0** | `SHOW TABLES FROM tcns` |

### Kết luận hiện trạng

**Mức đáp ứng bước 1 hiện tại: 0%.**

Agent đang lấy danh sách bảng bằng `SHOW TABLES` tại `agents/schema_agent.py:157`
→ **thấy toàn bộ 253 bảng**, không có bất kỳ giới hạn nào.

Trong đó có 57 bảng không ai mô tả, gồm những bảng nghe như bảng hệ thống:

```
Auth, DataPartition, DataPartitionUser, DangKyNghiHoc,
DangKyMoNganh, DangKySachEd, ChinhSachGiaoAn,
DanhMucPhong, DanhMucMucChuanDauRa, DmLoaiKhuyetTat,
DonDangKyChuyenNganh, DonDangKyChuyenNganhBuocXuLy, ...
```

Không có view nghiệp vụ nào được tạo.

---

## 2. Các việc cần làm

### Việc 1.1 — Chốt danh sách bảng agent được phép truy cập

**Mục tiêu:** Từ 253 bảng → còn danh sách bảng thực sự phục vụ hỏi đáp.

Chia làm 3 nhóm xử lý:

| Nhóm | Số lượng | Đề xuất xử lý |
|---|---|---|
| **A.** Có trong DB, không có metadata | 57 | **Loại bỏ** (mặc định) |
| **B.** Có metadata, không chứa cột nhạy cảm | ~171 | Rà soát, giữ bảng cần dùng |
| **C.** Có metadata, chứa cột nhạy cảm | 25 | Giữ nhưng **phải qua view** |

**Lý do loại nhóm A:** không có mô tả nghiệp vụ nghĩa là không phục vụ hỏi đáp.
Một số tên gợi ý đây là bảng hệ thống (`Auth`, `DataPartitionUser`) có thể chứa
dữ liệu phân quyền nội bộ — agent không nên biết chúng tồn tại.

**Về nhóm B:** kinh nghiệm cho thấy phần lớn câu hỏi thực tế chỉ chạm tới 30–50
bảng chính. Giữ lại toàn bộ 171 bảng vẫn chạy được, nhưng làm loãng vector search
và tăng nguy cơ agent chọn nhầm bảng.

> **Lưu ý:** Cột "Phân hệ" trong Excel **không dùng để phân nhóm tự động được** —
> chỉ 24/228 bảng có điền giá trị (QLĐT: 15, Cổng cán bộ: 8, QLDT: 1), 204 bảng
> còn lại bỏ trống. Việc phân nhóm phải làm thủ công.

**Đầu ra:** file `config/allowed_tables.yaml`

```yaml
qldt:
  - SinhVien
  - Diem
  - Nganh
  # ...
tcns: []
```

**Người thực hiện:** Anh + bộ phận nghiệp vụ (quyết định nghiệp vụ, không tự động hoá được)

---

### Việc 1.2 — Duyệt danh sách cột nhạy cảm

**Mục tiêu:** Xác định cột nào phải che khỏi agent.

Kết quả quét sơ bộ theo từ khóa (`lương`, `CCCD`, `tài khoản`, `ngân hàng`,
`mật khẩu`, `điện thoại`, `email`, `địa chỉ`, `ngày sinh`, `dân tộc`, `tôn giáo`,
`bảo hiểm`, `thuế`, `phụ cấp`, `thưởng`, `kỷ luật`):

**64 cột trong 25 bảng.** Tập trung nhiều nhất:

| Bảng | Số cột nhạy cảm |
|---|---|
| SinhVien | 15 |
| MucPhuCap | 5 |
| DangKyHocPhanTotNghiep | 3 |
| CauHinhQuyDoiGioGiangDay | 2 |
| ChuongTrinhDt | 2 |
| PhuHuynh | 2 |
| *(19 bảng khác)* | 1–2 mỗi bảng |

> **Con số 64 là ước tính máy quét, BẮT BUỘC phải có người duyệt.**
> Quét theo từ khóa nên vừa có thể sót (cột đặt tên lạ) vừa có thể thừa
> (ví dụ "email giảng viên" nếu là thông tin công khai thì không cần che).

**Đầu ra:** file `docs/cot_nhay_cam.md` — bảng gồm: tên bảng, tên cột,
tên tiếng Việt, kiểu dữ liệu, cột quyết định **[Che / Giữ]**

**Người thực hiện:** Anh + bộ phận nghiệp vụ

---

### Việc 1.3 — Tạo view cho các bảng nhạy cảm

**Mục tiêu:** Che cột nhạy cảm ở tầng DB.

Chỉ 25 bảng cần view, ~171 bảng còn lại dùng trực tiếp.

**Đề xuất:** gom view vào database riêng, không đổ vào `qldt`:

```sql
CREATE DATABASE agent_qldt;

CREATE VIEW agent_qldt.SinhVien AS
SELECT
    maSinhVien, hoTen, maNganh, khoaHoc   -- chỉ cột an toàn
    -- KHÔNG có: cccd, ngaySinh, danToc, tonGiao, diaChi, ...
FROM qldt.SinhVien;
```

**Vì sao tách database riêng:**
- Gỡ bỏ gọn: `DROP DATABASE agent_qldt` là sạch, không để lại vết trong `qldt`
- Không lẫn với bảng gốc của hệ thống khác đang dùng
- Dễ phân biệt khi backup / migrate

**Vì sao dùng view thay vì lọc cột ở tầng ứng dụng:**

| Tiêu chí | View (tầng DB) | Lọc cột (tầng app) |
|---|---|---|
| Công sức | 25 câu SQL | Parse `sqlglot` + resolve alias + UI |
| `SELECT *` | An toàn tự nhiên | Phải xử lý riêng |
| Dò qua `WHERE luong > 5tr` | Chặn được | Dễ sót |
| `sample_rows` rò dữ liệu | Tự động an toàn | Phải nhớ lọc riêng |
| Code có bug | Vẫn an toàn | Thủng |

Điểm quyết định là **`sample_rows`**: hiện `agents/schema_agent.py:142` chạy
`SELECT * FROM "{table}" LIMIT 3` và gửi nguyên 3 dòng dữ liệu thật vào prompt
OpenAI (`sql_gen_agent.py:51`, `sql_plan_agent.py:40`) — **kể cả khi không ai
hỏi tới cột đó**. Dùng view thì vấn đề này biến mất tự động.

**Người thực hiện:** Tôi sinh script sau khi có kết quả việc 1.2

---

### Việc 1.4 — Sửa code đọc theo allowlist

**Mục tiêu:** Agent chỉ thấy bảng trong danh sách đã duyệt.

| File | Sửa gì |
|---|---|
| `agents/schema_agent.py:157` | `_ch_fetch_all_tables` — lọc theo allowlist thay vì `SHOW TABLES` |
| `agents/schema_agent.py:109` | `_pg_fetch_all_tables` — tương tự cho Postgres |
| `agents/schema_agent.py:216` | `selected_tables` từ client — validate theo allowlist |
| `api/routers/tables.py:48` | `/api/v1/tables` — chỉ liệt kê bảng được phép |
| 25 bảng nhạy cảm | Trỏ sang `agent_qldt.<tên bảng>` thay vì `qldt.<tên bảng>` |

**Bắt buộc kèm theo — reindex Qdrant:**

`scripts/index_schema.py:64` hiện có logic:

```python
else:
    logger.info(f"Collection {collection_name} already exists. Skipping indexing.")
    continue
```

→ Gặp collection đã tồn tại là bỏ qua. **Nếu không xoá collection cũ rồi index
lại, việc sửa allowlist sẽ không có tác dụng** — agent vẫn dùng schema cũ đã
index sẵn trong Qdrant.

**Người thực hiện:** Tôi

---

### Việc 1.5 — Sửa lỗi cấu hình phát hiện trong quá trình khảo sát

Hai lỗi không thuộc phạm vi bước 1 nhưng ảnh hưởng trực tiếp:

**a) `.env` khai trùng biến:**

```
CH_DB_NAME=warehouse       ← không khớp tên biến nào trong config.py
CH_DB_NAME_TCNS=qldt       ← bị dòng dưới ghi đè
CH_DB_NAME_TCNS=tcns       ← dòng này thắng
```

Dòng thứ hai nhiều khả năng định viết `CH_DB_NAME_QLDT`. Hiện domain `qldt`
chạy được là nhờ **giá trị mặc định trong `config.py:24`**, không phải nhờ `.env`.

**b) Domain `tcns` có 0 bảng** nhưng endpoint `/api/v1/tcns/chat` vẫn mở và
nhận request. Cần xác nhận: chưa nạp dữ liệu, hay dữ liệu nằm ở database khác?

**Người thực hiện:** Anh xác nhận, tôi sửa

---

## 3. Bảng tổng hợp

| # | Việc | Người làm | Công sức | Chặn việc nào |
|---|---|---|---|---|
| 1.1 | Chốt danh sách bảng (loại 57, rà 196) | **Nghiệp vụ** | 1–2 ngày | 1.3, 1.4 |
| 1.2 | Duyệt 64 cột nhạy cảm | **Nghiệp vụ** | 0,5 ngày | 1.3 |
| 1.3 | Sinh script tạo 25 view | Tôi | 0,5 ngày | 1.4 |
| 1.4 | Sửa code + reindex Qdrant | Tôi | 0,5 ngày | — |
| 1.5 | Sửa `.env`, xác minh `tcns` | Anh + tôi | 0,5 giờ | — |

**Tổng: 2–3 ngày**, trong đó phần chờ nghiệp vụ duyệt (1.1 + 1.2) chiếm phần lớn.

### Đường găng

```
1.1 + 1.2  (nghiệp vụ duyệt)  →  1.3 (script view)  →  1.4 (sửa code + reindex)
                                      1.5 chạy song song, không phụ thuộc
```

Việc 1.1 và 1.2 là **quyết định nghiệp vụ**, không tự động hoá được, và chặn
toàn bộ các việc sau. Nên khởi động sớm nhất.

---

## 4. Mức đáp ứng sau khi hoàn thành

| | Trước | Sau bước 1 |
|---|---|---|
| Bước 1 (danh sách bảng / view) | 0% | **~95%** |
| *Toàn bộ 5 bước (tham chiếu)* | *~8%* | *~35%* |

Hoàn thành bước 1 giải quyết được:
- Agent không còn thấy 57 bảng hệ thống không liên quan
- 64 cột nhạy cảm được che ở tầng DB
- `sample_rows` không còn gửi dữ liệu nhạy cảm sang OpenAI

**Chưa giải quyết** (thuộc bước 2–5, ngoài phạm vi tài liệu này):
- Agent vẫn chạy dưới user `ript` (superuser) / `clickhouse` (toàn quyền)
- Chưa có role read-only → lệnh ghi chỉ chặn bằng regex ở tầng ứng dụng

---

## 5. Đề xuất bước tiếp theo

Để khởi động việc 1.1 và 1.2, tôi có thể xuất ngay 2 file để nghiệp vụ duyệt:

**`docs/danh_sach_bang.md`** — 253 bảng, mỗi dòng gồm:
- Tên bảng, số cột
- Có metadata hay không
- Phân hệ (nếu Excel có điền)
- Có chứa cột nhạy cảm hay không
- Cột trống **[Giữ / Loại]** để tick

**`docs/cot_nhay_cam.md`** — 64 cột, mỗi dòng gồm:
- Tên bảng, tên cột, tên tiếng Việt, kiểu dữ liệu
- Cột trống **[Che / Giữ]** để tick

Có hai file này thì việc 1.1 và 1.2 chỉ còn là tick chọn, phần còn lại là cơ học.

---

## Phụ lục — Nguồn số liệu

Toàn bộ số liệu đo trực tiếp ngày 11/09/2026:

| Số liệu | Cách lấy |
|---|---|
| 253 bảng | `SHOW TABLES FROM qldt` qua HTTP ClickHouse `192.168.30.28:18123` |
| 228 bảng / 3.075 cột | Đọc `QLDT_FINAL.xlsx`, sheet "Database Schema" |
| 57 bảng thiếu metadata | So khớp tên giữa hai nguồn trên |
| 64 cột / 25 bảng nhạy cảm | Quét regex từ khóa trên cột "Tên tiếng Việt" và "Tên thuộc tính" |
| 0 bảng `tcns` | `SHOW TABLES FROM tcns` |
| Phân hệ 24/228 | `value_counts()` trên cột "Phân hệ" |

**File liên quan:**
- `agents/schema_agent.py` — lấy schema, dòng 109 / 142 / 157 / 216
- `scripts/index_schema.py` — index Qdrant, dòng 64
- `api/routers/tables.py` — endpoint liệt kê bảng, dòng 48
- `config.py` — cấu hình DB, dòng 16–33
- `.env` — biến môi trường (có lỗi khai trùng)
