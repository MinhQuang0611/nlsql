# Bước 5 — Chỉ cho phép AI Agent truy cập qua USER có role agent

> **Yêu cầu gốc (anh Dũng - CNS):**
> *"5. Chỉ cho phép AI Agents truy cập qua USER role agent."*

**Ngày khảo sát:** 11/09/2026
**Phạm vi:** Chỉ bước 5. Bước 1/2/3/4 xem các tài liệu tương ứng.
**Trạng thái:** Chưa bắt đầu — 0%

---

## 1. Đặc điểm riêng của bước 5

Đây là **bước duy nhất trong 5 bước phải đụng vào ứng dụng**. Bốn bước trước chỉ
chạy SQL trên DB, không sửa code.

Bước 5 có hai mức độ:

| Mức | Nội dung | Công sức |
|---|---|---|
| **Mức tối thiểu** | Đổi `.env` sang user mới | 15 phút, **không sửa code** |
| **Mức đầy đủ** | Tách credential theo domain, chặn đường vòng | Nửa ngày, **có sửa code** |

Mức tối thiểu đã đạt được phần lớn mục tiêu. Mức đầy đủ xử lý nốt các kẽ hở.

---

## 2. Hiện trạng (đo thực tế)

### Các đường kết nối tới DB nguồn

Khảo sát toàn bộ code, có **3 nơi** tạo kết nối tới DB nguồn:

| Vị trí | Dùng cho | Credential |
|---|---|---|
| `db/connection.py:217` | ClickHouse sync engine | `settings.db_user` / `db_password` |
| `db/connection.py:249` | Postgres async engine | `settings.db_user` / `db_password` |
| `config.py:120,144` | Sinh chuỗi kết nối | `pg_db_user` hoặc `ch_db_user` |

Tất cả đều lấy từ **một cặp** `db_user` / `db_password` (`config.py:51-56`).

### Vấn đề: một credential dùng chung cho mọi domain

`db/connection.py:203-265` tạo engine cho cả 2 domain trong vòng lặp:

```python
domains = ["qldt", "tcns"]
for domain in domains:
    _pg_url = settings.get_database_url(domain)   # ← cùng user/password
    engines[domain] = create_async_engine(_pg_url, ...)
```

`get_database_url(domain)` chỉ đổi **tên database**, giữ nguyên user/password
(`config.py:130`). Nghĩa là:

```
qldt  →  postgresql://ript:***@192.168.30.28:16543/qldt
tcns  →  postgresql://ript:***@192.168.30.28:16543/tcns
             ↑ cùng một user
```

### Bảng đánh giá

| Hạng mục | Hiện trạng |
|---|---|
| User agent đang dùng | `ript` (Postgres) / `clickhouse` (ClickHouse) |
| Quyền của user đó | **Superuser** / **toàn quyền WITH GRANT OPTION** |
| Số credential cho 2 domain | **1** (dùng chung) |
| Engine tạo lúc nào | **Lúc import module** — cố định cả vòng đời ứng dụng |
| Có kiểm soát ai gọi domain nào | **Không** — endpoint public, domain lấy từ URL |

**Mức đáp ứng bước 5: 0%.**

---

## 3. Nội dung cần làm

### 3.1. Mức tối thiểu — đổi `.env` (15 phút, không sửa code)

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

Rồi khởi động lại ứng dụng.

**Sau bước này agent đã chạy dưới quyền read-only.** Đây là phần mang lại giá trị
lớn nhất với công sức nhỏ nhất trong toàn bộ 5 bước.

### 3.2. Tách credential theo domain (cần sửa code)

Hiện `config.py` chỉ có một cặp user/password. Để mỗi domain một user riêng:

**Thêm vào `config.py`:**

```python
pg_db_user_qldt: str = ""
pg_db_password_qldt: str = ""
pg_db_user_tcns: str = ""
pg_db_password_tcns: str = ""

def get_db_user(self, domain: str = "qldt") -> str:
    # ưu tiên credential riêng theo domain, không có thì dùng chung
    specific = getattr(self, f"{'pg' if self.active_db=='postgres' else 'ch'}_db_user_{domain}", "")
    return specific or self.db_user
```

**Sửa `config.py:120` và `config.py:144`** — dùng `get_db_user(domain)` thay cho
`self.db_user`.

**Không cần sửa `db/connection.py`** — vòng lặp tạo engine đã truyền `domain` vào
`get_database_url(domain)`, nên tự động dùng đúng credential.

**Vì sao cần tách:** hiện `/qldt/chat` và `/tcns/chat` đều public, không
authentication — ai gọi được cái này thì gọi được cái kia bằng cách đổi URL.
Nếu dùng chung một user có quyền cả hai database thì việc tách role ở bước 2
không có tác dụng bảo vệ.

### 3.3. Rà soát các đường vòng

*"Chỉ cho phép"* nghĩa là phải bịt mọi đường khác. Cần kiểm tra:

| Đường | Hiện trạng | Việc cần làm |
|---|---|---|
| Engine chính (`db/connection.py`) | Dùng `.env` | Tự động đúng sau 3.1 |
| `scripts/index_schema.py` | Dùng chung `settings` | Tự động đúng |
| `scripts/test_db_connection.py` | Dùng chung `settings` | Tự động đúng |
| `scripts/test_asynch.py:21` | **Hard-code** `clickhouse+asynch://default:@localhost:9000/nlsql` | Script test cũ — nên xoá hoặc sửa |
| `alembic.ini` | `sqlalchemy.url` để trống | Không ảnh hưởng |
| Kết nối thủ công (pgAdmin, DBeaver) | Người dùng tự nối | Ngoài phạm vi kỹ thuật |

`scripts/test_asynch.py` trỏ tới `localhost` nên không chạm DB sản xuất, nhưng là
credential hard-code trong code — nên dọn.

### 3.4. Xác minh không còn kết nối bằng tài khoản cũ

Sau khi chuyển đổi, kiểm tra trên DB:

```sql
-- Xem các kết nối đang hoạt động
SELECT usename, application_name, client_addr, state, COUNT(*)
FROM pg_stat_activity
WHERE datname IN ('qldt','tcns')
GROUP BY 1,2,3,4;
```

**Kỳ vọng:** chỉ thấy `nlsql_agent_qldt`, không còn `ript` từ IP của ứng dụng.

Nếu vẫn thấy `ript` → còn đường kết nối chưa chuyển, cần rà lại mục 3.3.

---

## 4. Giới hạn của bước 5 — cần nêu rõ

Bước 5 đảm bảo **agent chạy dưới user đúng quyền**. Nhưng nó **không** kiểm soát
được *ai* đang dùng agent.

```
Người dùng bất kỳ (không cần đăng nhập)
      ↓
POST /api/v1/qldt/chat   hoặc   /api/v1/tcns/chat     ← tự chọn domain
      ↓
Agent kết nối bằng nlsql_agent_qldt                    ← bước 5 lo phần này
      ↓
DB chặn lệnh ghi, chặn bảng ngoài quyền                ← bước 2,3,4 lo phần này
```

| Bước 5 giải quyết | Bước 5 KHÔNG giải quyết |
|---|---|
| Agent không còn quyền superuser | Ai được phép dùng agent |
| Lệnh ghi bị DB chặn | Ai được hỏi domain nào |
| Không đọc được DB khác | Ai được hỏi bảng nào |

Ba dòng bên phải cần **authentication + phân quyền theo account** — nằm ngoài
phạm vi 5 bước này.

Hiện `user_id` là trường client tự khai trong JSON (`api/schemas/chat.py:19`),
không ai kiểm chứng. Endpoint `/api/v1/*` không có lớp xác thực nào.

---

## 5. Kiểm thử

### 5.1. Xác nhận ứng dụng dùng đúng user

```bash
# Khởi động lại và xem log
docker compose restart app
docker compose logs app | grep -i "db ok\|connect"
```

Hoặc chạy script có sẵn:

```bash
python scripts/test_db_connection.py
# Kỳ vọng dòng "User : nlsql_agent_qldt"
```

### 5.2. Kiểm thử chức năng

| Kiểm tra | Kỳ vọng |
|---|---|
| Gọi `/api/v1/qldt/chat` câu hỏi thường | **Trả lời đúng như trước** |
| Câu hỏi có `JOIN` nhiều bảng | **Trả lời được** |
| Endpoint `/health` | `status: healthy` |
| `error.log` | Không có lỗi quyền |
| `/api/v1/tables?domain=qldt` | Liệt kê được bảng |

### 5.3. Kiểm thử bảo mật

Thử ép agent sinh lệnh ghi (ví dụ hỏi *"xoá tất cả sinh viên"*):

| Kỳ vọng | Ý nghĩa |
|---|---|
| DB trả `permission denied` | **Lớp chặn tầng DB hoạt động** |
| Ứng dụng báo lỗi, không crash | Xử lý lỗi đúng |

Trước bước 5, lệnh này có thể **thực thi thật** vì `ript` là superuser và lớp chặn
regex ở `agents/executor_agent.py:71` đang bị vô hiệu hoá (`.env` đặt
`APP_ENV=development` nên điều kiện `!= "development"` luôn false).

---

## 6. Bảng tổng hợp

| # | Việc | Người làm | Công sức | Sửa code |
|---|---|---|---|---|
| 5.1 | Đổi `.env` sang user mới | Anh | 15 phút | **Không** |
| 5.2 | Khởi động lại, kiểm thử | Anh + tôi | 30 phút | Không |
| 5.3 | Tách credential theo domain | Tôi | 2 giờ | **Có** |
| 5.4 | Dọn `scripts/test_asynch.py` hard-code | Tôi | 10 phút | Có |
| 5.5 | Xác minh `pg_stat_activity` | Anh | 10 phút | Không |

**Mức tối thiểu (5.1 + 5.2): 45 phút.**
**Mức đầy đủ: khoảng nửa ngày.**

### Rủi ro

| | |
|---|---|
| Có sửa dữ liệu không | **Không** |
| Có gián đoạn dịch vụ không | **Có** — cần restart ứng dụng |
| Rollback | Đổi lại `.env` về `ript`, restart |

**Rủi ro thực tế cần lưu ý:** nếu bước 3 cấp quyền thiếu bảng nào đó, agent sẽ
báo lỗi khi người dùng hỏi tới bảng đó. Nên thực hiện ngoài giờ cao điểm và kiểm
thử một loạt câu hỏi thật trước khi coi là xong.

---

## 7. Quan hệ với các bước khác

```
Bước 2 (CREATE ROLE) → Bước 3 (GRANT) → Bước 4 (CREATE USER + gán role)
                                                    ↓
                                        Bước 5 (app đổi sang user đó)  ← tài liệu này
```

**Bước 5 phụ thuộc toàn bộ bước 2, 3, 4.** Đổi `.env` sang một user chưa tồn tại
hoặc chưa được cấp quyền sẽ làm ứng dụng không khởi động được
(`main.py:66` kiểm tra kết nối DB lúc startup và raise `RuntimeError` nếu thất bại).

**Bước 5 là bước kích hoạt** — bốn bước trước chỉ chuẩn bị, không có tác dụng gì
cho tới khi bước 5 hoàn thành.

---

## 8. Mức đáp ứng sau khi hoàn thành

| | Trước | Sau 5.1+5.2 | Sau đầy đủ |
|---|---|---|---|
| Bước 5 riêng | 0% | **~85%** | **100%** |
| *Toàn bộ 5 bước* | *~8%* | *~50%* | *~55%* |

Chưa đạt 100% ở mức tối thiểu vì 2 domain vẫn dùng chung credential.

**Giải quyết được:**
- Agent không còn quyền superuser
- Lệnh ghi bị DB chặn tuyệt đối, không phụ thuộc regex đang tắt
- Không đọc được `pg_authid`, không sang được database `ript`/`vbcc`

**Chưa giải quyết** (ngoài phạm vi 5 bước):
- 64 cột nhạy cảm vẫn đọc được (cần bước 1)
- Không kiểm soát được ai dùng agent (cần authentication)
- SSL vẫn tắt, mật khẩu truyền không mã hoá

---

## Phụ lục — Nguồn số liệu

Khảo sát code ngày 11/09/2026:

| Nội dung | Vị trí |
|---|---|
| 3 nơi tạo kết nối DB nguồn | `db/connection.py:217,249`; `config.py:120,144` |
| Một credential dùng chung 2 domain | `config.py:51-56`, `config.py:130` |
| Engine tạo lúc import module | `db/connection.py:203-265` |
| Credential hard-code | `scripts/test_asynch.py:21` |
| Kiểm tra DB lúc startup | `main.py:66` |
| `user_id` client tự khai | `api/schemas/chat.py:19` |
| Lớp chặn ghi bị vô hiệu hoá | `agents/executor_agent.py:71` |
