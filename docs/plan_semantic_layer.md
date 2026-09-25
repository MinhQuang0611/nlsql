# Kế hoạch xây dựng Semantic Layer cho nlsql

> Cập nhật: **2026-09-25** (bản 3: chốt phạm vi "đang học", đã tạo tài khoản, bổ sung nguồn schema trong `text2sql/`).
>
> Tài liệu liên quan:
> - [TONG_QUAN_BAI_TOAN_VA_NGHIEN_CUU.md](TONG_QUAN_BAI_TOAN_VA_NGHIEN_CUU.md) — lý do và bằng chứng từ nghiên cứu
> - [TRANG_THAI_HIEN_TAI.md](TRANG_THAI_HIEN_TAI.md) §9.2, §9.3 — hai lỗi mà semantic layer phải sửa
> - [ke_hoach_cai_tien.md](ke_hoach_cai_tien.md) Bước 5 — bản phác `metric_router` / `metric_compiler` đầu tiên.
>   Bản phác đó viết cho pipeline 16 node cũ; kế hoạch này cập nhật theo pipeline 13 node sau đợt 3–4.
> - [plan_gioi_han_quyen_agent.md](plan_gioi_han_quyen_agent.md) — kế hoạch phân quyền; phần đăng nhập ở đây là nền cho kế hoạch đó

## Mục lục

1. [Mục tiêu](#1-mục-tiêu)
2. [Hiện trạng đầu vào](#2-hiện-trạng-đầu-vào)
3. [Quyết định thiết kế](#3-quyết-định-thiết-kế)
4. [Định dạng định nghĩa](#4-định-dạng-định-nghĩa)
5. [Lưu trữ, duyệt và đồng bộ git](#5-lưu-trữ-duyệt-và-đồng-bộ-git)
6. [Giao diện và đăng nhập](#6-giao-diện-và-đăng-nhập)
7. [Tích hợp vào pipeline hỏi đáp](#7-tích-hợp-vào-pipeline-hỏi-đáp)
8. [Lộ trình theo giai đoạn](#8-lộ-trình-theo-giai-đoạn)
9. [Danh mục chỉ tiêu đợt đầu](#9-danh-mục-chỉ-tiêu-đợt-đầu)
10. [Quyết định đã chốt và việc còn mở](#10-quyết-định-đã-chốt-và-việc-còn-mở)
11. [Đo lường](#11-đo-lường)
12. [Rủi ro](#12-rủi-ro)

---

## 1. Mục tiêu

Semantic layer biến nghĩa nghiệp vụ từ **lời khuyên trong prompt** thành **định nghĩa được khai báo, được người có thẩm quyền duyệt, và được kiểm chứng trên DB**.

Hai lỗi đo được mà nó phải sửa:

| Lỗi | Ví dụ | Vì sao prompt không đủ |
|---|---|---|
| Nghĩa nghiệp vụ (§9.2) | "Lượt học" phải đếm `DiemHocPhan`, agent từng chọn `LopHocPhan` rồi `HocPhanCtdt` | Không gì trong schema nói "lượt học" là gì |
| Giá trị enum (§9.3) | LLM viết `'DANG_HOC'`, giá trị thật là `'Đang học'` | SQL qua được EXPLAIN nhưng trả 0 dòng |

Kết quả mong muốn, đo được:

- Câu hỏi khớp một chỉ tiêu đã duyệt cho **cùng một SQL mọi lần chạy**, và **không có sai âm thầm**.
- Execution accuracy tổng thể trên benchmark mở rộng **không giảm** so với trước.
- Người nghiệp vụ **tự soạn và sửa định nghĩa trên web**; admin **đăng nhập để duyệt** trước khi định nghĩa có hiệu lực.
- Mọi bản định nghĩa đã xuất bản có **lịch sử trong DB và trong git**.
- Câu hỏi đi nhánh chỉ tiêu tốn **2 lượt LLM** thay vì 3.

Ngoài phạm vi: join chéo `qldt` × `tcns`, fine-tune model, phân quyền dữ liệu theo người hỏi (thuộc kế hoạch phân quyền, nhưng dùng lại hệ thống đăng nhập xây ở đây).

---

## 2. Hiện trạng đầu vào

### 2.1. Tri thức nghiệp vụ đang nằm rải rác ở bốn nơi

| Nơi | Nội dung | Vấn đề |
|---|---|---|
| `config.TABLE_RULES` | Quy tắc cho 6 bảng: `SinhVien`, `Nganh`, `KhoaNganh`, `DiemHocPhan`, `KqhtTichLuy`, `KqhtHocKy` | Văn bản tự do, viết cứng trong code, người nghiệp vụ không sửa được |
| Bảng `QuyDinhNghiepVu` + `knowledge_collection` | `tu_khoa` → `dinh_nghia_sql_logic`, đồng bộ từ Google Sheet | Trộn quy chế dạng văn bản với logic SQL; không có người duyệt hay phiên bản |
| `config/few_shot_qldt.json` | 10 cặp câu hỏi → SQL đã chạy thật | Là ví dụ, không phải định nghĩa |
| `QLDT_FINAL.xlsx` | Tên tiếng Việt cho bảng và cột, khoá ngoại | Xem 2.2 |

`TABLE_RULES` được đọc ở ba chỗ: `agents/schema_agent.py` (luôn đưa bảng có rule vào ứng viên, và đưa rule vào prompt chọn bảng) và `utils/schema_format.py` (gắn "Quy tắc (BẮT BUỘC)" vào schema cho `sql_gen`).

Hệ thống hiện **chưa có đăng nhập** ở bất kỳ tầng nào (xem [DANH_GIA_PHAN_QUYEN_TONG_HOP.md](DANH_GIA_PHAN_QUYEN_TONG_HOP.md)). Hai trang quản trị tĩnh `static/manage_knowledge.html` và `static/manage_faq.html` đang mở cho mọi người.

### 2.2. File Excel là nguồn tốt nhưng chưa sạch

Số liệu đọc bằng `utils/excel_metadata.py` ngày 2026-09-25:

| Chỉ số | Giá trị |
|---|---|
| Bảng có mô tả | 228 / 253 bảng trong DB |
| Cột có tên tiếng Việt | 3.075 |
| Cột "Mô tả" có nội dung | **0** |
| Cột "Từ đồng nghĩa" có nội dung | **0** |
| Cột có metadata enum hoặc ghi chú tham chiếu | 159 |
| Tên tiếng Việt có dấu hiệu dịch sai | khoảng 106 |

Ví dụ tên dịch sai cần sửa trước khi dùng làm nguồn:

| Bảng.cột | Tên trong Excel | Nghĩa đúng |
|---|---|---|
| `DiemHocPhan.diemThang4` | Điểm tháng 4 | Điểm hệ 4 |
| `DiemHocPhan.maHocPhan` | Mã bài tập | Mã học phần |
| `KqhtHocKy.trungBinhTichLuyToanKhoa` | Trung bình tích lũy toán học | Trung bình tích lũy toàn khoá |
| `SinhVien._id` | ID học phần | ID sinh viên |

### 2.3. Các điểm mơ hồ đã thấy trong schema

- `SinhVien` có ba cột ngành: `maNganh`, `maChuyenNganh`, `maNganh2`. "Ngành của sinh viên" mặc định là `maNganh`.
- `SinhVien.maKhoaNganh → KhoaNganh.ma`, và `KhoaNganh.maNganh → Nganh.ma`. Có hai đường JOIN tới `Nganh`, `TABLE_RULES` chọn đường trực tiếp.
- `KqhtTichLuy` được mô tả "một dòng mỗi sinh viên", nhưng bảng có `thuTuHocKy` và benchmark dùng `count(DISTINCT sinhVienSsoId)`. **Cần xác minh grain** trước khi khai báo chỉ tiêu trên bảng này.
- Khoá JOIN với sinh viên là `ssoId`: `DiemHocPhan.sinhVienSsoId`, `KqhtTichLuy.sinhVienSsoId`, `KqhtHocKy.sinhVienSsoId` đều trỏ `SinhVien.ssoId`.

### 2.4. Domain `tcns`

DB `tcns` tồn tại nhưng có 0 bảng. Qdrant còn 161 điểm schema từ lần index cũ, chứng tỏ từng có một nguồn dữ liệu. Repo **không có** file dump hay script nạp. Việc nạp dữ liệu cần nguồn từ hệ thống nhân sự (xem 10.2).

### 2.5. Thư mục `text2sql/`

Thư mục chứa bốn file **mô tả schema**, không chứa dữ liệu dòng. Đối chiếu ngày 2026-09-25:

| File | Nội dung | Khác với bản đang dùng |
|---|---|---|
| `QLDT_FINAL.xlsx` | 228 bảng, 3.075 cột | Giống hệt file ở thư mục gốc |
| `Database QLĐT (2).xlsx` | 229 bảng, 3.081 cột | Thêm bảng `HamSinhMa`; sửa 4 tên tiếng Việt, trong đó có chỗ vẫn sai (`DeTaiKhoaHoc._id` thành "ID điểm danh"). Cột "Mô tả", "Từ đồng nghĩa" vẫn trống |
| `VBCC_Final.xlsx`, `Database Schema VBCC (2).xlsx` | 10 bảng, 157 cột, hai bản giống nhau về bảng | Domain **văn bằng chứng chỉ**: `SoVanBang`, `PhuLucVanBang`, `DotCapBang`, `QuyetDinh`, `NguoiKyVanBang`, `YeuCauXacMinhVanBang`, `BieuMauPhuLuc`, `MucDichTraCuuPhuLuc`, `Ipfs`, `so_luot_tra_cuu` |

Không file nào mô tả schema nhân sự `tcns`. VBCC là một domain mới, chưa có trong Domain Registry (xem 10.2).

---

## 3. Quyết định thiết kế

### 3.1. Tự viết "MDL-lite", không nhúng engine ngoài

| Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|
| **Định nghĩa JSON/YAML + trình biên dịch Python trong repo** | Nhỏ, kiểm soát hoàn toàn; khớp LangGraph hiện có | Tự viết compiler và giao diện | **Chọn** |
| Wren semantic engine (MDL, Rust) | Có sẵn relationship, calculated field, dịch dialect | GenBI Classic đã sunset; thêm service Rust | Không nhúng, nhưng **giữ cấu trúc gần MDL** |
| dbt MetricFlow | Engine metric chín muồi | Cần dự án dbt; adapter ClickHouse của cộng đồng; không có giao diện duyệt | Không chọn |
| Cube | Semantic layer đầy đủ, có API | Thêm một hệ thống phải vận hành | Không chọn |

Cấu trúc dùng các khái niệm chung của MDL, OSI và MetricFlow: entity, relationship, dimension, metric, segment. Nếu sau này cần chuyển sang engine chuẩn, việc chuyển là đổi định dạng, không phải định nghĩa lại nghiệp vụ.

### 3.2. Hai cách dùng semantic layer, làm theo thứ tự

| | Chế độ A — Grounding | Chế độ B — Compile |
|---|---|---|
| Làm gì | Đưa định nghĩa, tên gọi, giá trị enum, đường JOIN vào schema retrieval và prompt `sql_gen` | LLM chỉ chọn chỉ tiêu, chiều, bộ lọc; Python ghép SQL từ định nghĩa |
| Áp dụng cho | Mọi câu hỏi dữ liệu | Chỉ câu khớp chỉ tiêu **đã duyệt** |
| Bảo đảm | Giảm xác suất sai | SQL tất định, không sai âm thầm trong phạm vi đã khai báo |
| Rủi ro | Thấp | Chọn nhầm chỉ tiêu cho câu gần giống |

### 3.3. Điều kiện lọc phải được khai báo, hiển thị và duyệt

Chỉ tiêu được phép mang điều kiện lọc mặc định **khi điều kiện đó là một phần của định nghĩa đã duyệt**. Ví dụ theo quyết định 10.1: "Tổng số sinh viên" = số sinh viên có `trangThaiHoc = 'Đang học'`, và **chỉ** giá trị này. "Bảo lưu" và "Chưa phân lớp" không tính vào, mà được đếm riêng qua câu hỏi gợi ý.

Ba ràng buộc đi kèm:

1. Điều kiện nằm trong định nghĩa, không nằm trong prompt, nên LLM không tự thêm hay bớt.
2. Câu trả lời **luôn nói rõ** điều kiện đã áp dụng, ví dụ "Hiện có 12.345 sinh viên đang học".
3. Chỉ tiêu có điều kiện mặc định phải khai báo **câu hỏi gợi ý** cho từng trường hợp bị loại ra: đã tốt nghiệp, thôi học, bảo lưu, chưa phân lớp. Gợi ý này đi vào `recommend_questions` của câu trả lời.

Quy tắc chung trong prompt `sql_gen` ("không tự thêm điều kiện lọc") vẫn giữ cho câu **không** có định nghĩa. Khi có định nghĩa, định nghĩa thắng; prompt phải nói rõ thứ tự ưu tiên này.

### 3.4. Biểu thức viết một lần, dịch sang từng dialect bằng SQLGlot

Biểu thức viết theo SQL chuẩn (PostgreSQL). Compiler dùng [SQLGlot](https://github.com/tobymao/sqlglot) để dịch sang ClickHouse hoặc PostgreSQL theo engine của domain. Khi dịch không đúng, cho phép ghi đè bằng `expr_by_dialect`. SQLGlot cũng dùng để thay regex chặn lệnh ghi trong `sql_check`, nên chỉ thêm một dependency.

### 3.5. DB là nơi soạn và vận hành, git là bản lưu đã duyệt

Theo quyết định 10.2, định nghĩa lưu ở cả hai nơi, với vai trò khác nhau:

| | PostgreSQL nội bộ | Git (`config/semantic/<domain>.yml`) |
|---|---|---|
| Vai trò | Nơi soạn, duyệt, xuất bản; runtime đọc từ đây | Bản snapshot của mỗi lần xuất bản; lịch sử và review kỹ thuật |
| Ai ghi | Giao diện web qua API | Job đồng bộ sau mỗi lần xuất bản; lập trình viên qua merge request |
| Chứa gì | Bản nháp, bản chờ duyệt, bản đã duyệt, các release | Chỉ release đã xuất bản |

Không có ghi hai chiều tự do. Thay đổi đến từ git (do lập trình viên sửa YAML) được **nhập vào DB dưới dạng bản nháp** và vẫn phải qua duyệt trên web. Nhờ vậy DB luôn là nguồn chân lý duy nhất lúc chạy, và git luôn phản ánh đúng những gì đã được duyệt.

---

## 4. Định dạng định nghĩa

Mỗi đối tượng (entity, relationship, dimension, segment, metric, glossary) được lưu dưới dạng JSON trong DB. Khi xuất ra git, toàn bộ release được ghi thành một file YAML theo cấu trúc dưới đây.

```yaml
version: 1
domain: qldt
release: 12                        # số release trong DB, ghi khi xuất bản

entities:
  sinh_vien:
    table: SinhVien
    key: ssoId                     # khoá dùng để JOIN
    business_key: ma               # mã sinh viên hiển thị cho người dùng
    label: Sinh viên
    aliases: [sinh viên, SV, học viên]
    grain: Một dòng là một sinh viên
    columns:
      trangThaiHoc:
        label: Trạng thái học
        values: [Đang học, Đã tốt nghiệp, Thôi học, Chưa phân lớp, Bảo lưu]
        value_aliases:
          Đang học: [đang theo học, còn học, chưa ra trường]
          Đã tốt nghiệp: [tốt nghiệp, đã ra trường]
      gioiTinh:   { label: Giới tính, values: [Nam, Nữ] }
      namNhapHoc: { label: Năm nhập học, type: year, aliases: [khoá, năm vào trường] }
      maNganh:    { label: Mã ngành chính, note: "Không dùng maNganh2 / maChuyenNganh trừ khi hỏi rõ" }
    pii: [cccd, soDienThoai, email, soTaiKhoanNganHang, ngaySinh]   # không bao giờ SELECT

  nganh:
    table: Nganh
    key: ma
    label: Ngành đào tạo
    aliases: [ngành, ngành học]

  diem_hoc_phan:
    table: DiemHocPhan
    key: _id
    label: Điểm học phần
    grain: Một dòng là một lượt học của một sinh viên với một học phần
    columns:
      diemTongKet: { label: Điểm tổng kết hệ 10 }
      diemThang4:  { label: Điểm hệ 4 }

relationships:
  - { name: sv_nganh, from: sinh_vien.maNganh, to: nganh.ma, type: many_to_one }
  - { name: diem_sv, from: diem_hoc_phan.sinhVienSsoId, to: sinh_vien.ssoId, type: many_to_one }
  - { name: diem_hp, from: diem_hoc_phan.maHocPhan, to: hoc_phan.ma, type: many_to_one }

dimensions:
  nganh:        { label: Ngành, entity: nganh, column: ten, via: [sv_nganh] }
  gioi_tinh:    { label: Giới tính, entity: sinh_vien, column: gioiTinh }
  nam_nhap_hoc: { label: Năm nhập học, entity: sinh_vien, column: namNhapHoc, type: year }
  trang_thai:   { label: Trạng thái học, entity: sinh_vien, column: trangThaiHoc }
  hoc_phan:     { label: Học phần, entity: hoc_phan, column: ten, via: [diem_hp] }

segments:
  sv_dang_hoc:
    label: Sinh viên đang học
    entity: sinh_vien
    filter: "trangThaiHoc = 'Đang học'"
    aliases: [đang học, đang theo học, còn học]
  sv_da_tot_nghiep: { label: Sinh viên đã tốt nghiệp, entity: sinh_vien, filter: "trangThaiHoc = 'Đã tốt nghiệp'" }
  sv_thoi_hoc:      { label: Sinh viên thôi học, entity: sinh_vien, filter: "trangThaiHoc = 'Thôi học'" }
  sv_bao_luu:       { label: Sinh viên bảo lưu, entity: sinh_vien, filter: "trangThaiHoc = 'Bảo lưu'" }
  sv_chua_phan_lop: { label: Sinh viên chưa phân lớp, entity: sinh_vien, filter: "trangThaiHoc = 'Chưa phân lớp'" }

metrics:
  so_sinh_vien:
    label: Tổng số sinh viên (đang học)
    entity: sinh_vien
    expr: count(*)
    default_segments: [sv_dang_hoc]          # quyết định 10.1
    aliases: [tổng số sinh viên, bao nhiêu sinh viên, số sinh viên]
    dimensions: [nganh, gioi_tinh, nam_nhap_hoc]
    answer_note: "Chỉ tính sinh viên có trạng thái Đang học (không gồm bảo lưu, chưa phân lớp)"
    suggest:
      - Có bao nhiêu sinh viên đã tốt nghiệp?
      - Có bao nhiêu sinh viên thôi học?
      - Có bao nhiêu sinh viên đang bảo lưu?
      - Có bao nhiêu sinh viên chưa phân lớp?
      - Số sinh viên theo từng trạng thái học
    owner: Phòng Đào tạo
    verified_by: ""                          # hệ thống ghi khi admin duyệt
    verified_at: ""

  so_sinh_vien_theo_trang_thai:
    label: Số sinh viên theo trạng thái học
    entity: sinh_vien
    expr: count(*)
    dimensions: [trang_thai]
    aliases: [đã tốt nghiệp, thôi học, bảo lưu, tất cả sinh viên]

  so_luot_hoc:
    label: Số lượt học
    entity: diem_hoc_phan
    expr: count(*)
    aliases: [lượt học, số lần học]
    dimensions: [hoc_phan]

glossary:
  - term: học lực
    note: Không nói học kỳ thì dùng KqhtTichLuy; nói rõ học kỳ thì dùng KqhtHocKy
```

Quy tắc kiểm tra, chạy khi bấm "Kiểm tra" trên web, trước khi duyệt, lúc startup và trong CI:

1. Mọi bảng và cột tồn tại trong DB, đối chiếu qua `db/introspect.py`.
2. Mọi `values` là tập con của giá trị phân biệt thật trong DB.
3. Mọi relationship JOIN được và không nhân bản dòng ngoài dự kiến so với `type`.
4. Mọi chỉ tiêu biên dịch được cho từng engine, qua `EXPLAIN` và chạy ra ít nhất một dòng.
5. Không chỉ tiêu hay chiều nào tham chiếu cột trong `pii`.
6. Chỉ tiêu có `default_segments` phải có `answer_note` và ít nhất một `suggest`.
7. Tham chiếu chéo hợp lệ: metric trỏ tới entity, dimension, segment đã tồn tại trong cùng release.

---

## 5. Lưu trữ, duyệt và đồng bộ git

### 5.1. Bảng trong PostgreSQL nội bộ

Tạo bằng alembic trong `db/migrations/versions/`, cùng DB với lịch sử chat.

| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `app_user` | `id`, `username`, `full_name`, `password_hash`, `role`, `active`, `must_change_password`, `created_at`, `last_login_at` | **Đã tạo** ngày 2026-09-25. `role` ∈ `editor`, `approver`, `admin` |
| `semantic_object` | `id`, `domain`, `kind`, `key`, `status`, `draft_version_id`, `published_version_id`, `owner` | Duy nhất theo (`domain`, `kind`, `key`) |
| `semantic_version` | `id`, `object_id`, `version_no`, `spec` (JSONB), `change_note`, `author_id`, `created_at`, `validation` (JSONB), `status`, `reviewer_id`, `reviewed_at`, `review_comment` | Mỗi lần lưu là một phiên bản mới, không sửa đè |
| `semantic_release` | `id`, `domain`, `release_no`, `snapshot` (JSONB), `yaml_sha256`, `git_commit`, `published_by`, `published_at` | Snapshot toàn bộ model tại thời điểm xuất bản |
| `audit_log` | `id`, `actor_id`, `action`, `object_ref`, `before`, `after`, `at` | Ghi mọi thao tác đăng nhập, sửa, duyệt, xuất bản |

### 5.2. Vòng đời một định nghĩa

```
nháp ──(Gửi duyệt)──► chờ duyệt ──(Duyệt)──► đã duyệt ──(Xuất bản)──► có hiệu lực
  ▲                        │
  └──────(Từ chối, kèm lý do)──┘
```

Quy tắc:

- Chỉ gửi duyệt được khi bảy quy tắc kiểm tra ở mục 4 đều qua.
- **Người duyệt khác người soạn.** API từ chối nếu `reviewer_id == author_id`.
- Duyệt thì hệ thống tự ghi `verified_by`, `verified_at` vào spec.
- Xuất bản gom mọi bản đã duyệt của domain thành một `semantic_release` mới. Runtime chỉ đọc release mới nhất.
- Quay lại bản cũ bằng cách xuất bản lại snapshot của release trước thành release mới. Lịch sử không bị xoá.

### 5.3. Nạp lại khi xuất bản

Server chạy `uvicorn --workers 2`, nên nạp lại trong một process là không đủ. Sau khi xuất bản:

1. Ghi `semantic:release:<domain>` = `release_no` vào Redis và phát sự kiện trên kênh `semantic:reload`.
2. Mỗi worker so `release_no` trong Redis với bản đang cache ở đầu mỗi request, lệch thì nạp lại từ DB.
3. Chạy lại phần index alias và giá trị trên Qdrant cho các entity thay đổi, dưới dạng tác vụ nền.
4. Xoá cache Redis kết quả truy vấn của domain đó, vì cùng câu hỏi có thể cho SQL khác.

### 5.4. Đồng bộ với git

| Chiều | Cách làm | Giai đoạn |
|---|---|---|
| DB → git | `scripts/semantic_sync.py export --domain qldt` ghi release mới nhất ra `config/semantic/qldt.yml`, kèm `release` và `yaml_sha256` | Bản đầu chạy tay sau mỗi lần xuất bản |
| DB → git, tự động | Job sau xuất bản đẩy file lên nhánh `semantic/auto-<domain>` và mở merge request qua API GitLab, rồi ghi `git_commit` vào `semantic_release` | Bản sau, cần token GitLab |
| git → DB | `scripts/semantic_sync.py import --file config/semantic/qldt.yml` tạo **bản nháp** cho các đối tượng khác bản đang có hiệu lực | Dùng khi lập trình viên sửa YAML |

Khi nhập từ git, nếu file dựa trên release cũ hơn release trong DB, script báo xung đột và không nhập, để tránh ghi đè thay đổi đã duyệt trên web.

CI chạy `scripts/validate_semantic.py` trên mọi merge request có sửa `config/semantic/`.

---

## 6. Giao diện và đăng nhập

### 6.1. Đăng nhập

Đây là hệ thống đăng nhập đầu tiên của nlsql, nên thiết kế để kế hoạch phân quyền dùng lại được.

- FastAPI: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`.
- Mật khẩu băm bằng scrypt của thư viện chuẩn Python (`utils/passwords.py`), không cần cài thêm gói. Phiên đăng nhập là JWT ký bằng `AUTH_SECRET`, đặt trong cookie `httpOnly`, `SameSite=Lax`, hết hạn sau 8 giờ.
- Tài khoản có `must_change_password = true` bị buộc đổi mật khẩu ngay sau lần đăng nhập đầu; cần endpoint `POST /api/v1/auth/change-password`.
- Dependency `require_role("approver")` gắn vào các endpoint duyệt và xuất bản.
- Giới hạn số lần đăng nhập sai theo IP bằng Redis.
- Tài khoản tạo bằng `python -m scripts.create_users` (đã có, xem 10.1), mật khẩu ngẫu nhiên, không có mật khẩu mặc định trong code.
- Hai trang tĩnh `manage_knowledge.html` và `manage_faq.html` được gắn cùng lớp đăng nhập, vì hiện đang mở công khai.

### 6.2. API semantic

| Endpoint | Quyền | Việc |
|---|---|---|
| `GET /api/v1/semantic/{domain}/objects?kind=&status=&q=` | editor | Danh sách, lọc, tìm |
| `GET /api/v1/semantic/objects/{id}` | editor | Chi tiết, kèm lịch sử phiên bản |
| `POST /api/v1/semantic/{domain}/objects`, `PUT /api/v1/semantic/objects/{id}` | editor | Tạo, sửa bản nháp |
| `POST /api/v1/semantic/objects/{id}/validate` | editor | Chạy kiểm tra, trả SQL đã dịch cho từng engine và 10 dòng kết quả mẫu |
| `POST /api/v1/semantic/objects/{id}/submit` | editor | Gửi duyệt |
| `GET /api/v1/semantic/reviews?status=pending` | approver | Hàng chờ duyệt |
| `POST /api/v1/semantic/reviews/{version_id}/approve`, `.../reject` | approver | Duyệt hoặc từ chối kèm lý do |
| `POST /api/v1/semantic/{domain}/publish` | approver | Xuất bản release mới |
| `GET /api/v1/semantic/{domain}/releases`, `.../releases/{no}/yaml` | editor | Lịch sử release, tải YAML |
| `POST /api/v1/semantic/{domain}/releases/{no}/rollback` | admin | Xuất bản lại một release cũ |

Router mới: `api/routers/auth.py`, `api/routers/semantic.py`.

### 6.3. Trang trong wren-ui

Đặt trong wren-ui vì đây là giao diện chính, và wren-ui đã có nhóm trang "Knowledge" (`/knowledge/instructions`, `/knowledge/question-sql-pairs`) cùng cơ chế proxy API sang backend như `/api/v1/chat/stream`.

| Trang | Ai dùng | Nội dung |
|---|---|---|
| `/login` | Mọi người dùng quản trị | Đăng nhập; cookie được proxy chuyển tiếp sang FastAPI |
| `/knowledge/semantic` | editor | Danh sách theo loại (chỉ tiêu, phân khúc, thực thể, chiều, thuật ngữ), nhãn trạng thái, ô tìm kiếm |
| `/knowledge/semantic/[id]` | editor | Form có cấu trúc cho từng loại; chọn bảng và cột từ danh sách thật; nút "Kiểm tra" hiện SQL cho ClickHouse và PostgreSQL cùng dữ liệu mẫu; tab "YAML" cho người rành kỹ thuật; lịch sử phiên bản |
| `/admin/review` — **tab Admin duyệt** | approver | Hàng chờ duyệt; so sánh bản mới với bản đang có hiệu lực theo từng trường; kết quả kiểm tra và dữ liệu mẫu; nút Duyệt, Từ chối kèm lý do; nút Xuất bản |
| `/admin/releases` | approver, admin | Lịch sử release, người xuất bản, commit git, tải YAML, quay lại bản cũ |
| `/admin/users` | admin | Tạo tài khoản, đổi vai trò, khoá tài khoản |

Tab Admin chỉ hiện trong sidebar khi `GET /auth/me` trả vai trò `approver` hoặc `admin`. Mọi kiểm tra quyền vẫn nằm ở FastAPI; giao diện ẩn nút chỉ để tiện dùng.

Upstream của wren-ui đã ngừng hỗ trợ, nên các trang này là mã nhóm tự sở hữu và tự bảo trì.

### 6.4. Hiển thị ở màn hình chat

- Câu trả lời từ nhánh chỉ tiêu có nhãn "Chỉ tiêu đã duyệt", tên chỉ tiêu, người duyệt và ngày duyệt.
- `answer_note` luôn xuất hiện trong câu trả lời, ví dụ "chỉ tính sinh viên đang học".
- Các câu `suggest` hiện thành nút hỏi tiếp.

---

## 7. Tích hợp vào pipeline hỏi đáp

### 7.1. Module mới

```
semantic/
  model.py      # pydantic: Entity, Relationship, Dimension, Segment, Metric, SemanticModel
  store.py      # đọc/ghi các bảng ở mục 5.1, tạo release
  loader.py     # nạp release mới nhất từ DB, cache theo domain, kiểm tra release_no trên Redis
  validate.py   # bảy quy tắc ở mục 4
  compiler.py   # (metric, dimensions, segments, filters) → SQL theo dialect, qua SQLGlot
  render.py     # phần grounding đưa vào prompt chọn bảng và sql_gen
scripts/
  gen_semantic_skeleton.py   # sinh bản nháp đầu từ Excel + introspect + profiling
  semantic_sync.py           # export / import giữa DB và git
  validate_semantic.py       # dùng trong CI
  create_users.py            # đã có
```

### 7.2. Chế độ A — thay `TABLE_RULES`

| Chỗ sửa | Thay đổi |
|---|---|
| `scripts/index_schema.py` | Payload bảng và cột lấy `label`, `aliases`, `values`, `value_aliases` từ release đang có hiệu lực. Tăng `INDEX_VERSION` |
| `agents/schema_agent.py` | Bảng có entity hoặc được glossary nhắc tới thay cho danh sách bảng trong `TABLE_RULES`. Điểm từ vựng khớp cả alias |
| `utils/schema_format.py` | Thay "Quy tắc (BẮT BUỘC)" bằng khối render: grain, giá trị enum, đường JOIN chuẩn, cột PII bị cấm |
| `prompts/sql_gen.py` | Thêm khối "ĐỊNH NGHĨA NGHIỆP VỤ ĐÃ DUYỆT" gồm chỉ tiêu và segment liên quan, kèm biểu thức đã dịch. Ghi rõ định nghĩa thắng quy tắc "không tự thêm điều kiện" |
| `config.py` | Xoá `TABLE_RULES` sau khi đã chuyển hết vào DB |

### 7.3. Chế độ B — nhánh compile

Mở rộng structured output của node `router` thay vì thêm node LLM mới:

```python
class MetricChoice(BaseModel):
    metric: str | None            # tên trong danh mục, None nếu không khớp
    dimensions: list[str] = []
    segments: list[str] = []      # segment người hỏi nêu rõ; thay cho default_segments nếu cùng cột
    filters: list[Filter] = []    # {dimension, op, value}; op ∈ =, >, <, >=, <=, between
```

Prompt router chỉ nhận danh mục rút gọn gồm tên, nhãn, alias, chiều và segment cho phép. Nó không thấy biểu thức, bảng hay điều kiện. Khi danh mục vượt khoảng 50 chỉ tiêu, lấy top-k bằng vector trước.

Chốt chặn bằng Python, bắt buộc:

- Chỉ dùng chỉ tiêu đã duyệt trong release đang có hiệu lực.
- Tên chỉ tiêu, chiều, segment không có trong release thì rơi về luồng `sql_gen`.
- Giá trị bộ lọc phải khớp `values` hoặc `value_aliases` sau khi bỏ dấu, hoặc đúng kiểu. Không khớp thì rơi về luồng `sql_gen`.
- Câu có ràng buộc không biểu diễn được bằng chiều hay bộ lọc đã khai báo thì router phải trả `metric = None`.
- Người hỏi nêu segment khác trên cùng cột với `default_segments`, ví dụ "sinh viên đã tốt nghiệp", thì segment của người hỏi thay cho segment mặc định.

Luồng sau khi thêm:

```
faq → router ──(khớp chỉ tiêu đã duyệt)──► metric_compiler ──► execute → data_check → chart → answer
          └──(không khớp)──► schema ∥ knowledge → retrieval_join → sql_gen → sql_check → execute → …
```

`metric_compiler` không gọi LLM và bỏ qua `schema`, `knowledge`, `sql_gen`. Vẫn chạy `EXPLAIN` một lần như chốt an toàn. State thêm `sql_source` (`metric` | `generated`), `metric_spec`, `release_no`. `ChatResponse` trả thêm các trường này để màn hình chat hiện nhãn ở mục 6.4.

---

## 8. Lộ trình theo giai đoạn

Công sức ghi bằng ngày công của một lập trình viên, là **ước lượng** chưa gồm thời gian chờ nghiệp vụ.

| GĐ | Việc | Sản phẩm | Tiêu chí xong | Công sức |
|---|---|---|---|---|
| 0 | Mở rộng benchmark lên khoảng 50 câu | Benchmark có `category`, `difficulty`, `expected_source`; sửa gold "Tổng số sinh viên" thành chỉ đếm đang học | Có câu dùng enum, "lượt học", học lực kỳ/tích luỹ, JOIN ngành; gold được người thứ hai duyệt | 2–3 |
| 1 | Lõi semantic | `semantic/model.py`, `validate.py`, `compiler.py`, `render.py`; bộ định nghĩa đầu cho 6 bảng trong `TABLE_RULES` | Validator chạy xanh trên ClickHouse và PostgreSQL; test đơn vị compiler | 4–6 |
| 2 | Lưu trữ và vòng đời | Migration mục 5.1, `store.py`, `loader.py`, nạp lại qua Redis, `semantic_sync.py` | Tạo, duyệt, xuất bản, quay lại chạy được bằng script; export ra YAML khớp snapshot | 3–4 |
| 3 | Đăng nhập và API | `auth.py` (gồm đổi mật khẩu), `semantic.py`, audit log; bảng `app_user` và `create_users.py` đã có; gắn đăng nhập cho hai trang tĩnh | Test API: người soạn không tự duyệt được; editor không xuất bản được | 4–5 |
| 4 | Giao diện wren-ui | `/login`, `/knowledge/semantic`, tab `/admin/review`, `/admin/releases`, `/admin/users` | Một người nghiệp vụ soạn, admin duyệt và xuất bản một chỉ tiêu mà không cần lập trình viên | 6–8 |
| 5 | Làm sạch nguồn và profiling | Sửa khoảng 106 tên dịch sai; nghiệp vụ điền mô tả, từ đồng nghĩa cho khoảng 20 bảng hay hỏi nhất; `values` cho cột chuỗi dưới 30 giá trị | Câu kiểu `'DANG_HOC'` trong benchmark ra đúng | 4 + thời gian nghiệp vụ |
| 6 | Chế độ A | Sửa các file ở mục 7.2, xoá `TABLE_RULES` | Benchmark không giảm so với GĐ0 | 3–4 |
| 7 | Chế độ B | Mở rộng router, node `metric_compiler`, nhãn ở màn hình chat | 15–20 chỉ tiêu đã duyệt; nhánh metric đúng 100% trên câu khớp; 0 câu gán nhầm trong bộ câu đối chứng | 5–7 |
| 8 | Domain `tcns` | Nạp dữ liệu, index schema, bộ định nghĩa đầu, benchmark `tcns` | Xem 10.2; `pii` cho lương và hồ sơ cá nhân xong trước chỉ tiêu | 3–5 sau khi có nguồn |
| 9 | Vận hành | Log `sql_source`, tỉ lệ rơi về luồng sinh SQL, câu không khớp; job tự mở merge request GitLab | Báo cáo tháng đầu tiên | 2–3 |

Tổng ước lượng khoảng 36–49 ngày công.

Thứ tự phụ thuộc:

- GĐ0 phải xong trước GĐ6 và GĐ7, vì không có benchmark thì không đo được cải thiện.
- GĐ1 → GĐ2 → GĐ3 → GĐ4 đi tuần tự. GĐ5 chạy song song với GĐ2–GĐ4.
- GĐ6 chỉ cần GĐ1 và GĐ2, nên có thể làm trước GĐ4 nếu muốn có lợi ích sớm. Khi đó định nghĩa đầu được duyệt bằng script.
- GĐ8 chạy song song khi có nguồn dữ liệu `tcns`.

---

## 9. Danh mục chỉ tiêu đợt đầu

Lấy từ 12 câu benchmark và 10 few-shot hiện có. Cột cuối là câu hỏi nghiệp vụ cần trả lời trên giao diện trước khi admin duyệt.

| Chỉ tiêu | Bảng | Biểu thức | Mặc định | Chiều | Cần nghiệp vụ xác nhận |
|---|---|---|---|---|---|
| `so_sinh_vien` | SinhVien | `count(*)` | Chỉ `Đang học` (đã chốt) | ngành, giới tính, năm nhập học, tỉnh quê quán | — |
| `so_sinh_vien_theo_trang_thai` | SinhVien | `count(*)` | — | trạng thái | — |
| `so_nganh` | Nganh | `count(*)` | — | trình độ | Có tính ngành đã dừng (`active`) không? |
| `so_khoa_nganh` | KhoaNganh | `count(*)` | — | ngành, năm bắt đầu | — |
| `so_luot_hoc` | DiemHocPhan | `count(*)` | — | học phần, học kỳ | Có tính lượt học lại, học cải thiện không? |
| `diem_tb_hoc_phan` | DiemHocPhan | `avg(diemTongKet)` | — | học phần | Có loại điểm quy đổi (`quyDoi`) không? |
| `ty_le_dat_hoc_phan` | DiemHocPhan | tỉ lệ `diemTongKet >= 4.0` | — | học phần | Ngưỡng đạt là 4.0 hệ 10 cho mọi học phần? |
| `gpa_tich_luy_tb` | KqhtTichLuy | `avg(trungBinhThang4)` | Có nên chỉ tính sinh viên đang học? | học lực, ngành | Xác minh grain của bảng (mục 2.3) |
| `so_sv_nhap_hoc` | SinhVien | `count(*)` | — (mọi trạng thái) | năm nhập học, ngành | Lấy theo `namNhapHoc` hay `ngayNhapHoc`? |
| `ty_le_gioi_tinh` | SinhVien | tỉ lệ Nam/Nữ | Theo `so_sinh_vien`? | ngành | Xử lý 8.862 dòng NULL giới tính thế nào? |

Segment đợt đầu: `sv_dang_hoc`, `sv_da_tot_nghiep`, `sv_thoi_hoc`, `sv_bao_luu`, `sv_chua_phan_lop`, `sv_quoc_tich_vn`. "Học lực giỏi", "sinh viên xuất sắc" chỉ thêm khi có văn bản quy chế làm căn cứ.

Quyết định "tổng số chỉ tính đang học" kéo theo câu hỏi cho các chỉ tiêu khác tính trên sinh viên. Mỗi chỉ tiêu cần ghi rõ có áp `sv_dang_hoc` hay không, để hai con số không mâu thuẫn trên cùng dashboard.

Rule trong `QuyDinhNghiepVu` có `dinh_nghia_sql_logic` là biểu thức SQL sẽ được `gen_semantic_skeleton.py` chuyển thành bản nháp segment hoặc chỉ tiêu, rồi đi qua duyệt như mọi định nghĩa khác. Rule dạng quy chế văn bản giữ nguyên trong `knowledge_collection`.

---

## 10. Quyết định đã chốt và việc còn mở

### 10.1. Đã chốt ngày 2026-09-25

| # | Câu hỏi | Quyết định | Ảnh hưởng tới kế hoạch |
|---|---|---|---|
| 1 | Ai duyệt định nghĩa | Đưa lên giao diện; admin đăng nhập vào tab riêng để duyệt | Mục 5.2, 6.1, 6.3; GĐ3–GĐ4 |
| 2 | Lưu định nghĩa ở đâu | Cả DB và git, có giao diện sửa trên web | Mục 3.5, 5; GĐ2 |
| 3 | "Tổng số sinh viên" đếm gì | Chỉ sinh viên đang học; gợi ý hỏi thêm đã tốt nghiệp, thôi học | Mục 3.3, 4, 9; sửa gold benchmark ở GĐ0 |
| 4 | Domain `tcns` | Nạp dữ liệu, không tắt domain | Mục 2.4; GĐ8 |
| 5 | Phạm vi "đang học" | Chỉ `trangThaiHoc = 'Đang học'`. "Bảo lưu" và "Chưa phân lớp" đếm riêng, đưa vào câu hỏi gợi ý | Mục 3.3, 4, 9 |
| 6 | Tài khoản ban đầu | Tạo sẵn vài tài khoản | Đã tạo 5 tài khoản, xem dưới |

Tài khoản đã tạo trong bảng `app_user` của Postgres nội bộ bằng `python -m scripts.create_users --seed`. Mật khẩu ngẫu nhiên nằm trong `secrets/initial_accounts.txt` (quyền 600, không commit). Mọi tài khoản phải đổi mật khẩu ở lần đăng nhập đầu, khi GĐ3 xong.

| Username | Vai trò | Dự kiến |
|---|---|---|
| `admin` | admin | Quản trị hệ thống |
| `duyet.daotao` | approver | Người duyệt Phòng Đào tạo |
| `duyet.nhansu` | approver | Người duyệt Phòng Tổ chức cán bộ |
| `soan.daotao` | editor | Người soạn Phòng Đào tạo |
| `soan.nhansu` | editor | Người soạn Phòng Tổ chức cán bộ |

Đổi tên hiển thị hoặc gán cho người thật bằng tab `/admin/users` sau GĐ4, hoặc tạo thêm bằng `python -m scripts.create_users --username ... --full-name ... --role ...`.

### 10.2. Việc còn mở

1. **Nguồn dữ liệu `tcns`.** Thư mục `text2sql/` không có schema nhân sự. Vẫn cần biết dữ liệu nhân sự lấy từ hệ thống nào, dạng gì (dump PostgreSQL, bản sao ClickHouse, file xuất), ai cấp quyền, và file Excel mô tả bảng như bên đào tạo. Trong lúc chờ, nên trả lời "dữ liệu nhân sự chưa sẵn sàng" thay vì báo lỗi.
2. **Domain VBCC.** Có schema 10 bảng văn bằng chứng chỉ trong `text2sql/`. Cần quyết định đây là domain thứ ba hay là thứ thay cho `tcns`, và dữ liệu VBCC nằm ở DB nào.
3. **Bản Excel QLĐT nào là chuẩn.** `Database QLĐT (2).xlsx` có thêm bảng `HamSinhMa` và sửa 4 tên, nhưng vẫn còn tên sai. Đề xuất dùng bản (2) làm nguồn sinh khung ở GĐ1, sau đó YAML/DB là nguồn chân lý.
4. **Token GitLab** cho job tự mở merge request ở GĐ9. Trước khi có token, export ra git chạy tay.
5. ~~**Migration alembic hỏng.**~~ **Đã sửa ngày 2026-09-25.** Revision `fc74da33ac26` từng DROP bảng chat thay vì tạo bảng FAQ, và `e1edb74afe77` rỗng. Cả hai đã được viết lại để tạo đúng bảng (bỏ qua nếu đã có); `db/migrations/env.py` loại các bảng chat và checkpoint khỏi autogenerate. DB đã sao lưu rồi nâng lên `a3c9e5f1d2b7`, dữ liệu chat giữ nguyên, `alembic check` không còn thay đổi nào.

---

## 11. Đo lường

Chạy benchmark 3 lần cho mỗi phiên bản, so sánh theo cặp trên cùng bộ câu.

| Chỉ số | Cách đo | Mục tiêu |
|---|---|---|
| Execution accuracy tổng | `scripts/run_bennmark.py` | Không thấp hơn mốc GĐ0 |
| Accuracy nhánh metric | Chỉ tính câu có `sql_source = metric` | 100% |
| Gán nhầm chỉ tiêu | Bộ câu đối chứng: câu gần giống chỉ tiêu nhưng có ràng buộc ngoài danh mục | 0 câu |
| Độ ổn định | Số câu cho kết quả khác nhau giữa 3 lần chạy | 0 ở nhánh metric |
| Độ phủ | Tỉ lệ câu thật đi nhánh metric, từ log | Theo dõi, không đặt mục tiêu ở đợt đầu |
| Lượt LLM và độ trễ | Log node | Nhánh metric: 2 lượt, dưới mức trung bình 7,1 giây hiện tại |
| Thời gian duyệt | Từ lúc gửi duyệt tới lúc xuất bản, từ `audit_log` | Theo dõi |

Harness benchmark cần ghi `sql_source` và `release_no` cho từng câu, và chấm theo subset match (cho phép thừa cột) như Defog sql-eval.

---

## 12. Rủi ro

| Rủi ro | Hậu quả | Giảm thiểu |
|---|---|---|
| Router gán câu vào chỉ tiêu gần giống nhưng khác nghĩa | Sai âm thầm | Chốt chặn mục 7.3; bộ câu đối chứng; câu trả lời luôn nêu định nghĩa và `answer_note` |
| Điều kiện mặc định "đang học" gây hiểu nhầm | Người dùng tưởng là toàn bộ sinh viên | `answer_note` bắt buộc; nút gợi ý hỏi đã tốt nghiệp, thôi học |
| Lỗ hổng ở hệ thống đăng nhập mới | Người ngoài sửa được định nghĩa, ảnh hưởng mọi câu trả lời | argon2, cookie httpOnly, giới hạn đăng nhập sai, kiểm tra quyền ở FastAPI, audit log, người duyệt khác người soạn |
| Người duyệt duyệt cho qua | Định nghĩa sai có hiệu lực | Màn hình duyệt bắt buộc hiện SQL và dữ liệu mẫu; quay lại release cũ bằng một thao tác |
| DB và git lệch nhau | Không biết bản nào đúng | DB là nguồn chân lý; git chỉ nhận snapshot release; nhập từ git thành bản nháp và kiểm tra xung đột theo `release_no` |
| Hai worker dùng hai release khác nhau | Cùng câu hỏi ra hai kết quả | Kiểm tra `release_no` trên Redis ở đầu mỗi request |
| Schema DB thay đổi | Định nghĩa trỏ tới cột không còn | Validator lúc startup và trong CI; định nghĩa lỗi bị tắt và báo trên tab Admin |
| SQLGlot dịch sai cho ClickHouse | Kết quả sai trên một engine | Validator chạy trên cả hai engine; `expr_by_dialect` để ghi đè |
| Tự bảo trì fork wren-ui | Tốn công vá lỗi Next.js và dependency | Giữ trang mới tách biệt, ít phụ thuộc phần lõi của wren-ui |
