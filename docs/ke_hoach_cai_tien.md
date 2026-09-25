# nlsql — Kế hoạch cải tiến độ chính xác

> Viết 2026-09-18. Mọi số liệu trong tài liệu đo trên DB thật (ClickHouse `qldt`, 51.125 sinh viên)
> và Qdrant thật (`nlsql_qdrant`), không phải ước lượng.
>
> **Mức độ chắc chắn** được ghi rõ ở từng bước. Đọc phần đó trước khi quyết định ưu tiên.

---

## Mục lục

1. [Vì sao cần cải tiến — số liệu đo được](#1-vì-sao-cần-cải-tiến)
2. [Bước 1 — Nạp knowledge & FAQ](#bước-1--nạp-knowledge--faq)
3. [Bước 2 — Sửa ngưỡng schema linking](#bước-2--sửa-ngưỡng-schema-linking)
4. [Bước 3 — Sửa TABLE_RULES sai tên cột](#bước-3--sửa-table_rules-sai-tên-cột)
5. [Bước 4 — Sửa prompt sinh SQL](#bước-4--sửa-prompt-sinh-sql)
6. [Bước 5 — Semantic layer (dài hạn)](#bước-5--semantic-layer-dài-hạn)
7. [Phụ lục — cách đo lại](#phụ-lục--cách-đo-lại)

---

## 1. Vì sao cần cải tiến

### 1.1 Số liệu đo được

Bộ test: 11 câu hỏi, SQL vàng đã verify chạy được trên DB thật. Mỗi câu chạy **3 lần**:

| Kết quả | Số câu |
|---|---|
| Đúng cả 3 lần | 5/11 |
| Báo lỗi (người dùng biết là hỏng) | 1/11 |
| **Sai âm thầm** (số sai, trông như đúng) | **5/11** |
| Cùng câu hỏi ra kết quả **khác nhau** giữa các lần | 4/11 |

### 1.2 Vì sao "sai âm thầm" là vấn đề nghiêm trọng nhất

Ví dụ thật, câu hỏi *"Có bao nhiêu ngành đào tạo?"*:

```sql
-- Đáp án đúng
SELECT count(DISTINCT ma) FROM Nganh;                                  -- → 76

-- Pipeline sinh ra
SELECT count(DISTINCT ma) FROM Nganh WHERE trangThaiDaoTao = 'Đang đào tạo';  -- → 0
```

LLM thấy cột tên `trangThaiDaoTao` nên **tự nghĩ ra** điều kiện lọc mà không ai yêu cầu.
Cột đó NULL 100% nên kết quả ra 0.

Điều nguy hiểm: SQL chạy thành công, trả về 1 dòng, không NULL → `data_check_agent` cho **PASS**.
Vòng lặp retry không kích hoạt. Người dùng nhận số 0 và tin là thật.

> **Nguyên tắc rút ra:** một hệ thống đúng 70% mà bạn không biết câu nào thuộc 30% còn lại
> thì không dùng được cho báo cáo. Kiểu lỗi quan trọng hơn tỉ lệ đúng.

### 1.3 Bốn nguyên nhân gốc

| # | Nguyên nhân | Bằng chứng | Bước sửa |
|---|---|---|---|
| 1 | Không có quy tắc nghiệp vụ | `knowledge_collection` = 0 điểm | Bước 1 |
| 2 | Schema linking chết | ngưỡng 0.68 > điểm cosine cao nhất 0.559 | Bước 2 |
| 3 | `TABLE_RULES` sai tên cột | `ma_sinh_vien`, `lan_thi` không tồn tại trong DB | Bước 3 |
| 4 | Prompt không hướng dẫn cách suy luận | chỉ nói "hãy sinh ra câu SQL chính xác" | Bước 4 |

Bốn bước trên đều là *giảm xác suất sai*. Bước 5 (semantic layer) đổi bản chất: **loại bỏ khả năng sai**
cho các chỉ tiêu quan trọng.

---

## Bước 1 — Nạp knowledge & FAQ

**Mức độ chắc chắn: CAO.** Kiểm chứng trực tiếp, không cần suy luận.

### Vấn đề

```
knowledge_collection   0 điểm    ← rỗng
faq_collection         0 điểm    ← rỗng
schema_collection_qldt 253 điểm
few_shot_collection_qldt 10 điểm
```

### Ý nghĩa của việc rỗng

**`faq_agent`** không bao giờ trúng → mọi câu hỏi đều chạy hết pipeline 16 node,
kể cả câu lặp đi lặp lại đã có câu trả lời soạn sẵn.

**`knowledge_agent`** luôn trả:
```python
{"knowledge_context": "", "business_context": []}
```

Kéo theo `sql_plan_agent` nhận chuỗi `"Không có quy định nghiệp vụ nào liên quan."`
(xem `_format_business_context()` trong [sql_plan_agent.py](../agents/sql_plan_agent.py)).

Nghĩa là pipeline **phải tự đoán** mọi quy ước nghiệp vụ. Đây là lý do gốc của lỗi
`WHERE trangThaiHoc='Tốt nghiệp'` (giá trị thật là `'Đã tốt nghiệp'`).

### Dữ liệu đầu vào — giá trị enum thật trong DB

Đã truy vấn để lấy giá trị thật, dùng làm nội dung knowledge:

```
trangThaiHoc (bảng SinhVien):
    'Đang học'       32.423
    'Đã tốt nghiệp'  17.394
    'Thôi học'        1.198
    'Chưa phân lớp'     105
    'Bảo lưu'             5
```

### Cách làm

Có 2 đường nạp, dùng chung `knowledge_collection`:

#### Đường A — Google Sheet (hàng loạt)

Cấu trúc sheet (xem [scripts/index_knowledge.py](../scripts/index_knowledge.py)):

| Cột A: Tiêu đề | Cột B: Nội dung | Cột C: Nguồn |
|---|---|---|
| Trạng thái học của sinh viên | Cột `SinhVien.trangThaiHoc` có 5 giá trị: 'Đang học', 'Đã tốt nghiệp', 'Thôi học', 'Chưa phân lớp', 'Bảo lưu'. Khi hỏi "sinh viên đang học" dùng `trangThaiHoc = 'Đang học'`. Khi hỏi "đã tốt nghiệp" dùng `trangThaiHoc = 'Đã tốt nghiệp'`. | DB introspection |

Chạy:
```bash
python scripts/index_knowledge.py          # upsert, giữ dữ liệu cũ
python scripts/index_knowledge.py --force  # xoá và index lại toàn bộ
```

#### Đường B — API/UI (từng rule)

```bash
curl -X POST http://localhost:8000/api/v1/knowledge \
  -H 'Content-Type: application/json' \
  -d '{
    "tu_khoa": "sinh viên đang học",
    "dinh_nghia_sql_logic": "SinhVien.trangThaiHoc = '\''Đang học'\''. Không tính thôi học, bảo lưu, đã tốt nghiệp."
  }'
```

Hoặc dùng trang `/manage_knowledge`.

### Đầu ra mong đợi

Sau khi nạp, `knowledge_agent` trả về:

```python
{
  "knowledge_context":
      "[Quy tắc nghiệp vụ: sinh viên đang học]\n"
      "SinhVien.trangThaiHoc = 'Đang học'. Không tính thôi học, bảo lưu, đã tốt nghiệp.",
  "business_context": [
    {"id": "12", "tu_khoa": "sinh viên đang học",
     "dinh_nghia_sql_logic": "SinhVien.trangThaiHoc = 'Đang học'. ..."}
  ]
}
```

`sql_plan_agent` nhận được:
```
- Từ khóa: sinh viên đang học
  Định nghĩa (Logic): SinhVien.trangThaiHoc = 'Đang học'. Không tính thôi học...
```

### Danh sách rule nên nạp trước

Ưu tiên theo thứ tự tác động:

1. **Giá trị enum** của các cột hay lọc — `trangThaiHoc`, `gioiTinh`, `hocLuc`
2. **Khoá JOIN chuẩn** giữa các bảng chính — `SinhVien.maNganh = Nganh.ma`
3. **Định nghĩa chỉ tiêu** hay hỏi — "sinh viên đang học", "GPA hệ 4 dùng cột `trungBinhThang4`"
4. **Cảnh báo dữ liệu** — `namNhapHoc` NULL 78% nên không dùng để thống kê theo năm

### Kiểm tra

```bash
curl -s http://localhost:63332/collections/knowledge_collection \
  | python3 -c "import sys,json; print('points:', json.load(sys.stdin)['result']['points_count'])"
```

Kỳ vọng: khác 0.

---

## Bước 2 — Sửa ngưỡng schema linking

**Mức độ chắc chắn: CAO.** Đo trực tiếp, sai hiển nhiên.

### Vấn đề

[agents/schema_agent.py:220](../agents/schema_agent.py#L220):
```python
SCORE_THRESHOLD = 0.68
passed = [(t, h) for t, h in best.items() if h.score >= SCORE_THRESHOLD]
```

Điểm cosine thực tế đo được:

| Câu hỏi | Điểm cao nhất |
|---|---|
| "Có bao nhiêu sinh viên đang học?" | 0.501 |
| "Thống kê số lượng sinh viên theo ngành" | 0.559 |
| "Phân bố sinh viên theo tỉnh thành" | 0.401 |

**Điểm cao nhất từng đạt: 0.559 < ngưỡng 0.68.** Không bảng nào qua được, `passed` **luôn rỗng**.

### Vì sao điểm thấp

`embed_text` trong Qdrant là đoạn văn dài liệt kê **mọi cột**:

```
"Bảng Assignment lưu thông tin về Bài tập lớp học phần.
 Các thông tin bao gồm: ID bài tập lớp học phần (_id), Thời gian tạo (createdAt),
 Thời gian cập nhật cuối cùng (updatedAt), Trạng thái kích hoạt (active), ..."
```

Câu hỏi thì ngắn (6–10 chữ). Cosine giữa một câu ngắn và một đoạn văn 200 chữ luôn nằm
quanh 0.4–0.55. **Ngưỡng bị đặt sai ngay từ đầu**, không phải dữ liệu hỏng.

### Hệ quả — code chết

[schema_agent.py:279](../agents/schema_agent.py#L279):
```python
if len(relevant_tables) < 2:          # luôn đúng vì passed rỗng
    ...                               # nhánh LLM fallback LUÔN chạy
```

Nghĩa là:
- Vector search + Qdrant là **code chết** — tốn 1 lần gọi embedding mỗi request rồi vứt kết quả
- Cái thực sự chọn bảng là **LLM fallback**, vốn viết làm đường lui khẩn cấp

### Đo các phương án

16 câu (10 few-shot + 6 viết lại độc lập), 253 bảng:

| Chiến lược | Recall | Đủ bảng | Bảng TB |
|---|---|---|---|
| ngưỡng 0.68 (hiện tại) | 0.0% | 0/16 | 0.0 |
| vector top-10 | 75.0% | 11/16 | 10.0 |
| vector top-20 | 81.2% | 12/16 | 20.0 |
| **LLM chọn từ top-30 có mô tả** | **75.0%** | **12/16** | **2.1** |
| UNION(LLM, vector top-5) | 78.1% | 12/16 | 6.2 |

> **Lưu ý quan trọng:** khi đo bằng *execution accuracy* (chạy SQL thật, so kết quả),
> phương án LLM **không hơn** luồng hiện tại (33.3% vs 33.3%). Lợi ích duy nhất đã kiểm chứng
> là **giảm 78% schema context** (2.1 bảng thay vì 10), tức tiết kiệm token.
> Recall cao không tự động thành SQL đúng.

### Cách sửa

Trong [agents/schema_agent.py](../agents/schema_agent.py):

**2a. Bỏ ngưỡng cứng, lấy top-K**
```python
# CŨ
SCORE_THRESHOLD = 0.68
passed = [(t, h) for t, h in best.items() if h.score >= SCORE_THRESHOLD]

# MỚI — không lọc theo điểm tuyệt đối, lấy K ứng viên đầu
TOP_K_CANDIDATES = 30
ranked = sorted(best.items(), key=lambda x: x[1].score, reverse=True)
candidates = ranked[:TOP_K_CANDIDATES]
```

**Vì sao:** điểm cosine tuyệt đối không có ý nghĩa ổn định giữa các câu hỏi. Thứ hạng thì có.

**2b. Đưa LLM danh sách có mô tả, bỏ trần "tối đa 5"**

[schema_agent.py:291](../agents/schema_agent.py#L291) hiện tại:
```python
"Hãy liệt kê tên các bảng CÓ THỂ LIÊN QUAN đến câu hỏi trên. Cố gắng chọn tối đa 5 bảng chính xác nhất.\n"
```

Hai vấn đề:
- Đưa LLM **253 tên bảng trần**, không mô tả → nó phải đoán bảng nào chứa gì
- Trần "5 bảng" là con số cố định: câu đơn giản cần 1 bảng thì LLM có xu hướng nhét đủ 5;
  câu phức tạp cần 7 bảng thì bị chặn → SQL chắc chắn sai

Sửa thành:
```python
desc = "\n".join(
    f"- {t}: {DESC[t].split('Các thông tin bao gồm')[0].strip()[:110]}"
    for t in candidates
)
prompt = (
    f"Câu hỏi người dùng: {user_query}\n\n"
    f"Các bảng ứng viên (đã lọc sơ bộ theo độ liên quan):\n{desc}\n\n"
    f"Quy tắc chọn bảng (RẤT QUAN TRỌNG):\n{rules_str}\n\n"
    "Chọn các bảng CẦN THIẾT để viết SQL trả lời câu hỏi, kể cả bảng cần JOIN. "
    "Không chọn dư bảng không dùng tới.\n"
    "Chỉ in tên bảng, mỗi dòng một tên, không giải thích."
)
```

**Vì sao bỏ trần:** thay con số cố định bằng **tiêu chí** ("đủ để viết được SQL").
Đo thực tế: khi bỏ trần, LLM chọn trung bình **2.1 bảng** — *ít hơn* mức 5 mà prompt cũ khuyến khích.
Cái trần không bảo vệ khỏi chọn thừa; nó chính là thứ gây ra chọn thừa.

### Đầu vào / đầu ra

**Vào:** `user_query`, `domain`
**Ra:** `relevant_tables`, `schema_context`

```python
# Trước khi sửa
{"relevant_tables": [], "schema_context": []}      # rỗng → kích hoạt fallback

# Sau khi sửa
{"relevant_tables": ["SinhVien", "Nganh"],
 "schema_context": [{...}, {...}]}
```

---

## Bước 3 — Sửa TABLE_RULES sai tên cột

**Mức độ chắc chắn: CAO.** Kiểm chứng bằng truy vấn `system.columns`.

### Vấn đề

[config.py:157](../config.py#L157) `TABLE_RULES` tham chiếu các cột **không tồn tại**:

```python
"SinhVien": "... ưu tiên COUNT(DISTINCT ma_sinh_vien) nếu join với bảng khác ...",
"Diem":     "Chỉ lấy điểm của lần thi cuối cùng (lan_thi = MAX(lan_thi)) ...",
```

Kiểm chứng trên DB:

```
cột ma_sinh_vien     xuất hiện ở 0 bảng     ← KHÔNG TỒN TẠI
cột lan_thi          xuất hiện ở 0 bảng     ← KHÔNG TỒN TẠI
cột ma               xuất hiện ở 59 bảng    ← tên thật
cột maNganh          xuất hiện ở 20 bảng    ← tên thật
```

Bảng `Diem` cũng **không tồn tại** trong DB (chỉ có `DiemHocPhan`).

### Ý nghĩa

`TABLE_RULES` được nhét vào prompt của cả `schema_agent` (fallback) và `sql_plan_agent`/`sql_gen_agent`
với nhãn **"Quy tắc (BAT BUOC)"**. Tức là đang **chủ động hướng dẫn LLM dùng tên cột sai**.

Đây là nhiễu có hại, không phải nhiễu trung tính.

### Cách sửa

```python
TABLE_RULES: dict[str, str] = {
    "SinhVien": (
        "Khi đếm số lượng sinh viên có JOIN với bảng khác, dùng COUNT(DISTINCT ma) "
        "để tránh trùng lặp. Khi hỏi về 'ngành học', JOIN với bảng Nganh qua "
        "SinhVien.maNganh = Nganh.ma, KHÔNG dùng KhoaNganh."
    ),
    "Nganh": (
        "Bảng đại diện cho ngành học. Khi câu hỏi nhắc 'Ngành', 'Ngành học', "
        "luôn dùng bảng này, không nhầm với KhoaNganh."
    ),
    "KhoaNganh": (
        "CHỈ dùng khi câu hỏi nhắc CỤ THỂ đến Khoa (Department). "
        "Hỏi về ngành (Major) thì dùng Nganh."
    ),
    "DiemHocPhan": (
        "Điểm theo học phần. Cột diemTongKet là điểm hệ 10, diemThang4 là hệ 4. "
        "Không có bảng tên 'Diem'."
    ),
    "KqhtTichLuy": (
        "Khi hỏi GPA hoặc điểm tích luỹ hệ 4 (ví dụ > 3.6), dùng cột trungBinhThang4. "
        "Chỉ dùng trungBinh khi nói về hệ 10."
    ),
}
```

### Nguyên tắc

Mọi tên bảng/cột trong `TABLE_RULES` phải verify bằng:
```sql
SELECT name FROM system.columns WHERE database='qldt' AND table='<tên bảng>';
```

---

## Bước 4 — Sửa prompt sinh SQL

**Mức độ chắc chắn: TRUNG BÌNH.** Đo được +9.1% nhưng trên 11 câu, chênh lệch đúng 1 câu.
Là tín hiệu đáng theo, chưa phải bằng chứng.

### Vấn đề

[prompts/sql_gen.py](../prompts/sql_gen.py) kết thúc bằng:
```
Hãy sinh ra câu SQL query chính xác dựa trên kế hoạch và schema trên.
```

Chỉ nói **"viết SQL đi"**, không hướng dẫn *cách nghĩ*.

### Đo được

11 câu, execution accuracy trên DB thật:

| Lối sinh SQL | Đúng |
|---|---|
| G1 — prompt hiện tại | 7/11 = 63.6% |
| G2 — chia nhỏ câu hỏi (divide-and-conquer) | 8/11 = 72.7% |
| G3 — theo kế hoạch thực thi (query-plan) | 8/11 = 72.7% |
| 3 prompt khác nhau + chọn theo cụm kết quả | 8/11 = 72.7% |
| **Đối chứng: 3× CÙNG một prompt** | **8/11 = 72.7%** |

> **Kết luận từ dòng đối chứng:** chạy 3 prompt khác nhau **không hơn** chạy 3 lần cùng một prompt.
> Lợi ích không đến từ "đa dạng prompt" mà từ việc **prompt G1 đang yếu hơn G2/G3**.
> Vì vậy chỉ cần sửa prompt, **không cần** xây cơ chế nhiều prompt.

### Cách sửa

Sửa `SQL_GEN_SYSTEM` trong [prompts/sql_gen.py](../prompts/sql_gen.py), thêm hướng dẫn cách suy luận:

```python
SQL_GEN_SYSTEM = """Bạn là một chuyên gia SQL giỏi cho hệ quản trị {dialect_name}.
...

### CÁCH SUY LUẬN (BẮT BUỘC theo thứ tự) ###
Trước khi viết SQL, hãy suy nghĩ theo KẾ HOẠCH THỰC THI:
1. Cần quét những bảng nào?
2. Lọc theo điều kiện gì? — CHỈ lọc những gì câu hỏi YÊU CẦU RÕ.
   KHÔNG tự thêm điều kiện mà câu hỏi không nhắc tới.
3. JOIN thế nào? Dùng khoá nào?
4. Gom nhóm / tổng hợp ra sao?
5. Sắp xếp và giới hạn thế nào?

### QUY TẮC SQL ###
{dialect_rules}
...
"""
```

### Vì sao câu "KHÔNG tự thêm điều kiện" quan trọng

Đây là câu nhắm trực tiếp vào lỗi đã đo được:

```sql
-- Câu hỏi: "Có bao nhiêu ngành đào tạo?"
SELECT count(DISTINCT ma) FROM Nganh WHERE trangThaiDaoTao = 'Đang đào tạo'
--                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
--                                   không ai yêu cầu, cột này NULL 100% → ra 0
```

### Chi phí

Sửa vài dòng chữ. **Không thêm lượt gọi LLM nào**, không đổi kiến trúc.

---

## Bước 5 — Semantic layer (dài hạn)

**Mức độ chắc chắn: CHƯA ĐO ĐƯỢC.** Script kiểm chứng đã viết nhưng API key hết credit
trước khi chạy. Phần dưới là thiết kế, không kèm số liệu thực nghiệm của repo này.

### Vì sao cần, dù 4 bước trên đã làm

Bốn bước trên đều là *giảm xác suất LLM viết sai SQL*. Vẫn là xác suất — bạn không bao giờ biết
câu nào thuộc phần sai còn lại. Với 5/11 câu sai âm thầm, đó là rủi ro không chấp nhận được
cho số liệu đưa vào báo cáo.

Semantic layer đổi bản chất: **LLM không được phép viết SQL** cho các chỉ tiêu đã định nghĩa.

### Tham chiếu

[Benchmark dbt 2026](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026), schema bảo hiểm thật,
11 câu × 20 lần chạy:

| Model | Text-to-SQL | Semantic Layer |
|---|---|---|
| Claude Sonnet 4.6 | 90.0% | 98.2% |
| GPT-5.3-Codex | 84.1% | 100.0% |

Điểm chính không phải con số mà là **kiểu lỗi**:

> "Với text-to-SQL, thất bại trông như một câu trả lời hợp lý nhưng sai.
> Với Semantic Layer, thất bại trông như một thông báo lỗi."

### 5.1 File định nghĩa chỉ tiêu

Tạo `config/metrics_qldt.yaml`:

```yaml
so_nganh_dao_tao:
  mo_ta: "Số lượng ngành đào tạo của trường"
  bang: Nganh
  do_luong: "count(DISTINCT ma)"
  dieu_kien: null                     # KHÔNG lọc gì — đã kiểm chứng đáp án đúng là 76
  chieu_cho_phep: {}

so_sinh_vien_dang_hoc:
  mo_ta: "Số sinh viên đang theo học (không tính thôi học, bảo lưu, đã tốt nghiệp)"
  bang: SinhVien
  do_luong: "count()"
  dieu_kien: "trangThaiHoc = 'Đang học'"
  chieu_cho_phep:
    nganh:      { join: "INNER JOIN Nganh n ON SinhVien.maNganh = n.ma", cot: "n.ten" }
    gioi_tinh:  { cot: "gioiTinh" }
    tinh_thanh: { cot: "tinhTpQueQuan" }

gpa_trung_binh:
  mo_ta: "Điểm trung bình tích luỹ hệ 4 của sinh viên"
  bang: KqhtTichLuy
  do_luong: "round(avg(trungBinhThang4), 3)"
  dieu_kien: "trungBinhThang4 IS NOT NULL"
  chieu_cho_phep:
    hoc_luc: { cot: "hocLuc" }
```

**Mỗi định nghĩa phải verify trên DB trước khi đưa vào file.**

### 5.2 Node mới `metric_router`

**Đọc:** `user_query`
**Ghi:** `metric_name`, `metric_group_by`, `metric_matched`

LLM chỉ làm **phân loại**, không viết SQL.

Prompt chỉ chứa danh mục rút gọn (~15 token/dòng, 20 metric ≈ 300 token):

```
Danh mục chỉ tiêu:
- so_nganh_dao_tao: Số lượng ngành đào tạo của trường (chiều: không có)
- so_sinh_vien_dang_hoc: Số sinh viên đang theo học (chiều: nganh, gioi_tinh, tinh_thanh)
- gpa_trung_binh: Điểm trung bình tích luỹ hệ 4 (chiều: hoc_luc)

Câu hỏi: Trường mình hiện còn bao nhiêu em chưa ra trường?

Chọn metric khớp và chiều nhóm. Không khớp thì trả KHONG_KHOP.
```

> **QUAN TRỌNG:** prompt **không chứa** `bang`, `do_luong`, `dieu_kien`, `join`.
> LLM không thấy được phần SQL nên **không thể sửa, bỏ, hay thêm điều kiện**.
> Đây chính là cơ chế ngăn lỗi `WHERE trangThaiDaoTao='Đang đào tạo'`.

Dùng structured output:
```python
class MetricChoice(BaseModel):
    metric: str              # tên trong danh mục, hoặc "KHONG_KHOP"
    group_by: str | None
```

**Chốt chặn bằng Python — bắt buộc có:**
```python
if res.metric not in METRICS:                     # LLM bịa tên
    return {"metric_matched": False}              # → rơi về luồng cũ

dims = METRICS[res.metric]["chieu_cho_phep"]
group_by = res.group_by if res.group_by in dims else None
```

Kể cả LLM bịa, Python chặn. Không có đường nào để tên không tồn tại lọt xuống bước sau.

### 5.3 Node mới `metric_compiler`

**KHÔNG gọi LLM.** Hàm Python thuần, ghép chuỗi từ file YAML.

```python
def compile_metric(metric_name: str, group_by: str | None) -> str:
    m = METRICS[metric_name]
    if not group_by:
        sql = f"SELECT {m['do_luong']} AS gia_tri FROM {m['bang']}"
        if m['dieu_kien']:
            sql += f" WHERE {m['dieu_kien']}"
        return sql

    dim = m['chieu_cho_phep'][group_by]
    sql = f"SELECT {dim['cot']} AS nhom, {m['do_luong']} AS gia_tri\nFROM {m['bang']}"
    if dim.get('join'):
        sql += f"\n{dim['join']}"
    if m['dieu_kien']:
        sql += f"\nWHERE {m['dieu_kien']}"
    sql += f"\nGROUP BY {dim['cot']}\nORDER BY gia_tri DESC"
    return sql
```

**"Tất định" nghĩa là:** cùng đầu vào → luôn cùng đầu ra. Chạy 1000 lần ra 1000 kết quả giống hệt.
Không nhiệt độ, không ngẫu nhiên.

Đối chiếu số đo: **4/11 câu hiện ra kết quả khác nhau giữa các lần**. Với `metric_compiler`,
con số đó thành 0 — không phải vì LLM giỏi hơn, mà vì **không còn LLM ở khâu đó**.

### 5.4 Luồng sau khi thêm

```
retrieval_join
      │
      ▼
 metric_router          ◄── LLM chỉ chọn tên chỉ tiêu
      │
 ┌────┴─────────────────┐
khớp                không khớp
 │                      │
 ▼                      ▼
metric_compiler      sql_plan → sql_gen → sql_check
(Python, KHÔNG LLM)     │
 │                      │
 └──────────┬───────────┘
            ▼
        execute → data_check → chart → answer → END
```

Luồng 16 node hiện tại **giữ nguyên**. Chỉ thêm một nhánh rẽ.

### 5.5 Ví dụ dữ liệu đầu vào / đầu ra

#### Ví dụ 1 — khớp, không chiều

```python
# Vào
{"user_query": "Có bao nhiêu ngành đào tạo?"}

# metric_router ghi
{"metric_name": "so_nganh_dao_tao", "metric_group_by": None, "metric_matched": True}

# metric_compiler ghi
{"final_sql": "SELECT count(DISTINCT ma) AS gia_tri FROM Nganh",
 "sql_source": "metric"}

# execute ghi
{"query_result": [{"gia_tri": 76}], "row_count": 1, "executor_error": None}

# answer ghi
{"answer": "Trường hiện có 76 ngành đào tạo.", "answer_format": "text"}
```

So với hiện tại: pipeline ra **0**. Sau khi sửa: **76**, và ra 76 mọi lần chạy.

#### Ví dụ 2 — khớp, có chiều nhóm

```python
# Vào
{"user_query": "Số sinh viên đang học theo từng ngành"}

# metric_router ghi
{"metric_name": "so_sinh_vien_dang_hoc", "metric_group_by": "nganh", "metric_matched": True}

# metric_compiler ghi
{"final_sql": """SELECT n.ten AS nhom, count() AS gia_tri
FROM SinhVien
INNER JOIN Nganh n ON SinhVien.maNganh = n.ma
WHERE trangThaiHoc = 'Đang học'
GROUP BY n.ten
ORDER BY gia_tri DESC"""}

# execute ghi (số thật từ DB)
{"query_result": [
   {"nhom": "Công nghệ thông tin",         "gia_tri": 10121},
   {"nhom": "Kỹ thuật điện tử viễn thông", "gia_tri":  3435},
   {"nhom": "Quản trị kinh doanh",         "gia_tri":  2910}
 ], "row_count": 36}
```

Điều kiện `trangThaiHoc='Đang học'` và cách JOIN đến từ **file định nghĩa**, không do LLM nghĩ ra.

#### Ví dụ 3 — không khớp, rơi về luồng cũ

```python
# Vào
{"user_query": "Sinh viên nào có nhiều môn học lại nhất kỳ vừa rồi?"}

# metric_router ghi
{"metric_matched": False, "metric_name": None}

# → đi sql_plan → sql_gen → sql_check → execute (luồng hiện tại)
```

Câu lạ vẫn trả lời được, chỉ là không có bảo đảm.

### 5.6 Lợi ích phụ — giảm chi phí

| | Số lượt gọi LLM |
|---|---|
| Luồng hiện tại | 5–6 (intent, sql_plan, sql_gen, chart, answer + domain_router) |
| Nhánh metric | **2** (metric_router, answer) |

`sql_check` cũng bỏ qua được với nhánh metric — SQL ghép từ template đã verify,
không cần EXPLAIN dry-run và không bao giờ cần LLM sửa lỗi.

### 5.7 Đánh đổi phải chấp nhận

1. **Chỉ trả lời được câu đã mô hình hoá.** Câu ngoài danh mục → rơi về đường đoán hoặc từ chối.
2. **Việc nặng nhất không phải code mà là định nghĩa nghiệp vụ.**
   "Sinh viên đang học" có tính bảo lưu không? "Ngành đào tạo" có tính ngành đã dừng không?
   Cần người biết nghiệp vụ quyết định.
3. **Con số benchmark là của schema khác.** 98.2% đo trên dữ liệu bảo hiểm sạch.
   Dữ liệu `qldt` bẩn hơn. Semantic layer *giúp* ở chỗ này — vì cách xử lý NULL được mã hoá
   một lần trong định nghĩa thay vì để LLM đoán mỗi lần — nhưng đừng kỳ vọng đúng con số đó.

---

## Phụ lục — cách đo lại

### Bộ test

11 câu hỏi kèm SQL vàng **đã verify chạy được trên DB thật**. Nguyên tắc:
mọi gold SQL phải chạy ra kết quả hợp lý thì mới giữ; câu nào trả 0 dòng thì loại
(vì không phân biệt được "SQL sai" với "đáp án đúng là rỗng").

> Bài học: lần đo đầu tiên tôi viết gold dùng cột `tinhThanh` — cột này **không tồn tại**,
> tên thật là `tinhTpQueQuan`. Hai câu bị loại oan. Luôn verify gold trước.

### Đo cái gì

**Execution accuracy** — chạy cả gold SQL lẫn SQL pipeline sinh ra, so **kết quả trả về**.
Đây là metric BIRD/Spider dùng.

Không dùng recall schema-linking làm thước đo chính: đã kiểm chứng recall 75% vs 0%
nhưng execution accuracy **ngang nhau** (33.3% vs 33.3%). Chọn đúng bảng không đảm bảo SQL đúng.

### Đo kiểu lỗi, không chỉ tỉ lệ đúng

Chạy mỗi câu **3 lần**, phân loại:

| Loại | Ý nghĩa |
|---|---|
| Đúng cả 3 lần | tin được |
| Báo lỗi | người dùng biết là hỏng — chấp nhận được |
| **Sai âm thầm** | số sai trông như đúng — **nguy hiểm nhất** |
| Không ổn định | cùng câu ra số khác nhau — không tin được |

### Lưu ý chi phí

Bộ eval đầy đủ tốn khoảng **185 lượt câu × 3 lượt LLM**, trong đó `sql_gen` dùng
`SQL_GEN_MODEL=gpt-5.4` với prompt ~5.000 token (do `schema_context` chứa bảng 113 cột).

Ước tính chi phí một lần chạy đầy đủ: **vài trăm nghìn đồng**.

Khuyến nghị khi chạy lại:
- Đặt `SQL_GEN_MODEL` thành bản mini cho riêng phần eval — kết luận so sánh prompt
  không phụ thuộc model đắt
- Chốt cách chấm điểm **trước** khi chạy, tránh chạy lại nhiều lần
- Bắt đầu với 4–5 câu để kiểm tra script, rồi mới chạy đủ bộ

### Bộ test nên mở rộng

11 câu là quá ít — chênh lệch 63.6% vs 72.7% chỉ là **1 câu**. Cần 30–50 câu
với gold SQL do người biết nghiệp vụ viết và verify, thì mọi thay đổi mới đo được đáng tin.

---

## Tổng kết thứ tự thực hiện

| # | Việc | Chi phí | Mức chắc chắn | Tốn API? |
|---|---|---|---|---|
| 1 | Nạp knowledge + FAQ | nhập liệu | CAO | không |
| 2 | Sửa ngưỡng 0.68 | vài dòng | CAO | không |
| 3 | Sửa TABLE_RULES | vài dòng | CAO | không |
| 4 | Sửa prompt sql_gen | vài dòng | TRUNG BÌNH | không |
| 5 | Semantic layer | dài hạn | chưa đo | có, khi eval |

Bốn bước đầu **không tốn API**, làm được ngay cả khi key hết credit.
