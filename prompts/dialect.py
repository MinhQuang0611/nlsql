"""
Quy tắc SQL riêng theo từng dialect.

Trước đây mọi prompt đều ghi cứng "chuyên gia SQL cho PostgreSQL", trong khi
ACTIVE_DB thực tế là ClickHouse. LLM vì thế được dạy sai cú pháp: bọc identifier
bằng double quote, dùng hàm ngày tháng của Postgres, và chia số nguyên mà không
ép kiểu — ClickHouse cắt phần thập phân nên mọi tỉ lệ phần trăm đều sai.

Mỗi domain có engine riêng (config.Settings.get_domain_engine), nên khối quy tắc
phải được chọn theo domain của request, không theo biến global.
"""

_LABELS = {
    "postgres": "PostgreSQL",
    "clickhouse": "ClickHouse",
}

# Quy tắc đúng với mọi dialect.
_COMMON_RULES = """- CHỈ SỬ DỤNG SELECT statements, KHÔNG dùng DELETE, UPDATE, INSERT, DROP, ALTER.
- CHỈ SỬ DỤNG các tables và columns có trong database schema được cung cấp. Không bịa cột.
- ĐẶC BIỆT LƯU Ý VỀ JOIN: Tuyệt đối KHÔNG dùng cột "_id" để JOIN giữa các bảng — đây là
  khoá kỹ thuật, không mang ý nghĩa liên kết nghiệp vụ. Phải JOIN bằng khoá nghiệp vụ thật
  (ví dụ: dùng "sv"."ssoId" = "kq"."sinhVienSsoId", KHÔNG dùng "sv"."_id").
- PHẢI JOIN rành mạch khi lấy cột từ nhiều bảng. Đặt alias rõ ràng cho từng bảng.
- Ở câu hỏi tổng quát, thêm LIMIT khoảng 100 nếu đề bài không yêu cầu lấy tất cả."""

_POSTGRES_RULES = """- BẮT BUỘC bọc TẤT CẢ tên bảng và tên cột bằng dấu ngoặc kép.
  Ví dụ đúng: SELECT "maSinhVien" FROM "SinhVien"   — Sai: SELECT maSinhVien FROM SinhVien
- Đặt single quote quanh string literal. KHÔNG đặt quote quanh số.
- Dùng ILIKE thay LIKE khi cần tìm kiếm không phân biệt hoa thường.
- Ép kiểu bằng CAST(x AS numeric) hoặc x::numeric.
- Hàm ngày tháng: DATE_TRUNC('month', col), EXTRACT(YEAR FROM col), NOW(), CURRENT_DATE.
- Đếm có điều kiện: COUNT(*) FILTER (WHERE dieu_kien) hoặc SUM(CASE WHEN ... THEN 1 ELSE 0 END)."""

_CLICKHOUSE_RULES = """- BẮT BUỘC bọc TẤT CẢ tên bảng và tên cột bằng dấu backtick.
  Ví dụ đúng: SELECT `maSinhVien` FROM `SinhVien`   — Sai: SELECT maSinhVien FROM SinhVien
- Đặt single quote quanh string literal. KHÔNG đặt quote quanh số.
- CẢNH BÁO PHÉP CHIA: ClickHouse chia hai số nguyên vẫn cho ra số nguyên bị cắt phần thập phân.
  Mọi phép tính tỉ lệ / phần trăm / trung bình PHẢI ép kiểu trước:
  Đúng : round(toFloat64(countIf(`diem` >= 4.0)) * 100 / count(), 2)
  Sai  : round(countIf(`diem` >= 4.0) * 100 / count(), 2)
- Đếm có điều kiện: dùng combinator countIf(dieu_kien) / sumIf(cot, dieu_kien) — ngắn và nhanh
  hơn SUM(CASE WHEN ...). KHÔNG dùng cú pháp COUNT(*) FILTER (WHERE ...) của PostgreSQL.
- Dùng ILIKE cho tìm kiếm không phân biệt hoa thường (ClickHouse có hỗ trợ).
- Ép kiểu bằng hàm chuyên dụng: toFloat64(x), toInt64(x), toString(x), toDate(x).
- Hàm ngày tháng: toYear(col), toMonth(col), toStartOfMonth(col), today(), now().
  KHÔNG dùng CURRENT_DATE, KHÔNG dùng EXTRACT(... FROM ...) kiểu PostgreSQL.
- NULL: dùng ifNull(x, giá_trị) hoặc coalesce(x, giá_trị).
- ClickHouse KHÔNG có ràng buộc khoá ngoại, nên schema không liệt kê foreign key.
  Phải suy ra quan hệ từ tên cột (ví dụ `maNganh` của bảng này khớp `ma` của bảng `Nganh`).
- KHÔNG dùng subquery tương quan (correlated subquery) — ClickHouse hỗ trợ rất hạn chế.
  Hãy viết lại bằng JOIN hoặc bằng hàm aggregate."""

_RULES = {
    "postgres": _POSTGRES_RULES,
    "clickhouse": _CLICKHOUSE_RULES,
}


def get_dialect_label(engine: str) -> str:
    """Tên hiển thị của engine, dùng để xưng hô trong prompt."""
    return _LABELS.get(engine, "SQL")


def get_dialect_rules(engine: str) -> str:
    """Khối quy tắc SQL đầy đủ (chung + riêng theo dialect)."""
    specific = _RULES.get(engine, _POSTGRES_RULES)
    return f"{_COMMON_RULES}\n{specific}"
