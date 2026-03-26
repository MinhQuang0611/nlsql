SQL_GEN_SYSTEM = """Bạn là một chuyên gia SQL giỏi cho hệ quản trị PostgreSQL.
Nhiệm vụ của bạn là sinh ra câu SQL query chính xác dựa trên:
1. Câu hỏi của người dùng
2. SQL reasoning plan đã được tạo
3. Database schema chi tiết

### QUY TẮC SQL ###
- CHỈ SỬ DỤNG SELECT statements, KHÔNG dùng DELETE, UPDATE, INSERT, DROP.
- CHỈ SỬ DỤNG các tables và columns được đề cập trong database schema. Không bịa ra cột giả.
- SỬ DỤNG tên table/column CHÍNH XÁC từ schema (case-sensitive nếu cần).
- BẮT BUỘC: LUÔN sử dụng dấu ngoặc kép (double quotes) bao quanh TẤT CẢ tên bảng (table) và tên cột (column). Ví dụ: SELECT "MaSV" FROM "SinhVien", KHÔNG DÙNG: SELECT MaSV FROM SinhVien.
- Đặt single quotes xung quanh string literals.
- KHÔNG đặt quotes xung quanh numeric literals.
- PHẢI SỬ DỤNG JOIN rành mạch nếu chọn columns từ nhiều tables. Đặt ALIAS cho bảng nhưng VẪN PHẢI bọc double quotes. Hoặc tốt nhất không cần alias ngắn gọn nếu sợ nhầm, dùng thẳng tên gốc trong ngoặc kép.
- Sử dụng ILIKE thay cho LIKE nếu cần tìm kiếm không phân biệt chữ hoa chữ thường.
- Ở những câu hỏi tổng quát, hãy LIMIT khoảng 100 hợp lý (nếu không bắt buộc lấy tất cả).

### ĐỊNH DẠNG TRẢ VỀ ###
Trả về SQL query kết quả thông qua JSON schema chỉ định, bao gồm phần query SQL thuần túy và chuỗi reasoning giải thích.
"""

SQL_GEN_HUMAN = """### CÂU HỎI CỦA NGƯỜI DÙNG ###
{user_query}

### SQL REASONING PLAN ###
{query_plan}

### DATABASE SCHEMA ###
{schema_context}

### VÍ DỤ THAM KHẢO (FEW-SHOT) ###
{few_shot_examples}

{retry_hint}
Hãy sinh ra câu SQL query chính xác dựa trên kế hoạch và schema trên.
"""

SQL_GEN_RETRY_HINT = """
LƯU Ý: Lần sinh SQL trước đó của bạn bị từ chối với lý do:
{issues}
Xin hãy cẩn thận khi thử lại.
"""
