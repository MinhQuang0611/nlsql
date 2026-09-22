from functools import lru_cache
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DomainConfig(BaseModel):
    """
    Mô tả một nguồn dữ liệu (một database) mà agent được phép truy vấn.

    Trước đây hệ thống chỉ có biến global `active_db`, nên mọi domain buộc phải
    nằm trên cùng một loại engine. DomainConfig tách quyết định đó xuống từng
    domain: qldt có thể ở ClickHouse trong khi tcns ở PostgreSQL.
    """
    name: str
    engine: Literal["postgres", "clickhouse"]
    db_name: str
    description: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    # Engine mặc định, dùng cho domain nào không khai báo override riêng.
    active_db: str = "postgres"

    # ── Domain registry ────────────────────────────────────────────────────
    # Danh sách domain được bật, phân tách bằng dấu phẩy.
    domains_enabled: str = "qldt,tcns"

    # Engine riêng cho từng domain. Để rỗng => dùng active_db.
    domain_engine_qldt: str = ""
    domain_engine_tcns: str = ""

    # Mô tả nghiệp vụ — router_agent dùng để chọn đúng DB cho câu hỏi.
    domain_desc_qldt: str = (
        "Quản lý đào tạo (QLĐT): sinh viên, ngành học, chuyên ngành, khoa, "
        "học phần, lớp học phần, điểm thi, điểm học phần, kết quả học tập, GPA, "
        "điểm tích luỹ, điểm danh, tuyển sinh, nhập học, tốt nghiệp, học bổng."
    )
    domain_desc_tcns: str = (
        "Tổ chức cán bộ - nhân sự (TCNS): cán bộ, giảng viên, nhân viên, "
        "phòng ban, đơn vị, chức vụ, ngạch bậc, hợp đồng lao động, lương, "
        "bảo hiểm, thi đua khen thưởng, đào tạo bồi dưỡng, nghỉ phép."
    )

    pg_db_host: str = "localhost"
    pg_db_port: int = 5432
    pg_db_name_qldt: str = "qldt"
    pg_db_name_tcns: str = "tcns"
    pg_db_user: str = "postgres"
    pg_db_password: str = ""

    ch_db_host: str = "localhost"
    ch_db_port: int = 8123
    ch_db_name_qldt: str = "qldt"
    ch_db_name_tcns: str = "tcns"
    ch_db_user: str = "default"
    ch_db_password: str = ""

    # Internal Backend DB
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"


    # ── Domain registry: accessor ──────────────────────────────────────────

    def list_domains(self) -> list[str]:
        """Danh sách domain đang bật, theo thứ tự khai báo."""
        return [d.strip() for d in self.domains_enabled.split(",") if d.strip()]

    def get_domain_engine(self, domain: str = "qldt") -> str:
        """
        Engine của một domain: 'postgres' hoặc 'clickhouse'.
        Ưu tiên override DOMAIN_ENGINE_<domain>, nếu rỗng thì rơi về ACTIVE_DB.
        """
        override = (getattr(self, f"domain_engine_{domain}", "") or "").strip().lower()
        return override or self.active_db.strip().lower()

    def get_domain_description(self, domain: str = "qldt") -> str:
        return (getattr(self, f"domain_desc_{domain}", "") or "").strip() or domain

    def get_db_name(self, domain: str = "qldt") -> str:
        prefix = "pg" if self.get_domain_engine(domain) == "postgres" else "ch"
        return getattr(self, f"{prefix}_db_name_{domain}", "") or domain

    def get_domain(self, domain: str = "qldt") -> DomainConfig:
        return DomainConfig(
            name=domain,
            engine=self.get_domain_engine(domain),
            db_name=self.get_db_name(domain),
            description=self.get_domain_description(domain),
        )

    def _conn_params(self, engine: str) -> tuple[str, int, str, str]:
        """(host, port, user, password) theo loại engine."""
        if engine == "postgres":
            return self.pg_db_host, self.pg_db_port, self.pg_db_user, self.pg_db_password
        return self.ch_db_host, self.ch_db_port, self.ch_db_user, self.ch_db_password

    # Giữ lại cho script chẩn đoán — phản ánh engine mặc định, không phải per-domain.
    @property
    def db_host(self) -> str:
        return self._conn_params(self.active_db)[0]

    @property
    def db_port(self) -> int:
        return self._conn_params(self.active_db)[1]

    @property
    def db_user(self) -> str:
        return self._conn_params(self.active_db)[2]

    @property
    def db_password(self) -> str:
        return self._conn_params(self.active_db)[3]

    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_echo: bool = False

    # LLM - OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Per-agent model configuration
    openai_model: str = "gpt-4o-mini"        # router, answer, chart, knowledge, schema agents
    sql_gen_model: str = "gpt-4o-mini"       # sql_gen agent (có thể dùng model mạnh hơn)
    recommend_model: str = "gpt-4o-mini"     # recommend utility

    # LLM parameters
    llm_temperature: float = 0.0             # default temperature cho deterministic agents
    recommend_temperature: float = 0.7       # temperature cho recommend (cho phép sáng tạo hơn)
    llm_max_tokens: int = 4096
    llm_timeout: int = 60                    # seconds

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Quy tắc chọn bảng / cột, chèn vào prompt sinh SQL với nhãn "BẮT BUỘC".
    # Mọi tên bảng/cột ở đây PHẢI tồn tại trong DB (kiểm chứng qua system.columns) —
    # bản cũ tham chiếu `ma_sinh_vien`, `lan_thi`, bảng `Diem` đều không tồn tại,
    # tức là đang chủ động dạy LLM dùng tên sai.
    TABLE_RULES: dict[str, str] = {
        "SinhVien": (
            "Khi đếm số sinh viên có JOIN với bảng khác, dùng COUNT(DISTINCT ma) để tránh trùng. "
            "Khi hỏi về 'ngành học' của sinh viên, JOIN với bảng Nganh qua SinhVien.maNganh = Nganh.ma, "
            "KHÔNG dùng KhoaNganh."
        ),
        "Nganh": (
            "Bảng ngành học. Khi câu hỏi nhắc 'Ngành', 'Ngành học' (ví dụ top 5 ngành), "
            "luôn dùng bảng này, không nhầm với KhoaNganh."
        ),
        "KhoaNganh": (
            "CHỈ dùng khi câu hỏi nhắc CỤ THỂ đến Khoa (Department). Hỏi về ngành (Major) thì dùng Nganh."
        ),
        "DiemHocPhan": (
            "Điểm theo học phần — MỖI DÒNG LÀ MỘT LƯỢT HỌC (một sinh viên học một học phần). "
            "'Lượt học', 'số lần học', 'số sinh viên đã học học phần X' → đếm dòng bảng này, "
            "KHÔNG dùng LopHocPhan hay HocPhanCtdt. diemTongKet là điểm hệ 10, diemThang4 là hệ 4. "
            "Không có bảng tên 'Diem'."
        ),
        "KqhtTichLuy": (
            "Kết quả học tập TÍCH LUỸ toàn khoá, một dòng mỗi sinh viên: GPA (trungBinhThang4 hệ 4, "
            "trungBinh hệ 10), tổng tín chỉ tích luỹ (tongSoTinChi), học lực (hocLuc). "
            "Câu hỏi về GPA / tín chỉ tích luỹ / học lực mà KHÔNG nhắc học kỳ cụ thể → dùng bảng này."
        ),
        "KqhtHocKy": (
            "Kết quả học tập theo TỪNG HỌC KỲ. CHỈ dùng khi câu hỏi nhắc rõ học kỳ; "
            "hỏi chung (không nói học kỳ nào) thì dùng KqhtTichLuy."
        ),
    }

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "nlsql"

    app_env: str = "development"
    # Cho phép agent chạy SQL ghi (INSERT/UPDATE/DROP/...). Mặc định TẮT ở mọi môi trường.
    # Trước đây quyền này được suy ra từ app_env, nên APP_ENV=development vô hiệu hoá
    # chốt chặn ngay trên DB thật. Nay phải bật tường minh.
    allow_write_sql: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8388
    log_level: str = "INFO"

    qdrant_host: str = "localhost"
    qdrant_port: int = 63332
    qdrant_url: str = "http://localhost:63332"
    qdrant_api_key: str | None = None
    
    redis_host: str = "localhost"
    redis_port: int = 6097
    redis_url: str = "redis://localhost:6097"

    google_sheet_url: str = ""
    google_sheets_credentials_file: str = "utils/ascendant-nova-478100-q0-a825170022ba.json"
    sheets_knowledge_id: str = "1zQAKdpIWs_rDo5E-8yYQ-u3bf-iO2QMyCSxHMMA-PNE"
    sheets_knowledge_name: str = "Trang tính 1"


    # Config cho DataBase Postgres
     
    def get_database_url(self, domain: str = "qldt") -> str:
        from urllib.parse import quote_plus
        engine = self.get_domain_engine(domain)
        host, port, user, password = self._conn_params(engine)
        db_name = self.get_db_name(domain)
        if engine == "clickhouse":
            native_port = 19000 if port == 18123 else port
            return (
                f"clickhouse+asynch://{user}:{quote_plus(password)}"
                f"@{host}:{native_port}/{db_name}"
            )
        else:
            return (
                f"postgresql+asyncpg://{user}:{quote_plus(password)}"
                f"@{host}:{port}/{db_name}"
                f"?ssl=disable"
            )

    @property
    def internal_database_url(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{quote_plus(self.postgres_password)}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            f"?ssl=disable"
        )

    def get_database_url_sync(self, domain: str = "qldt") -> str:
        from urllib.parse import quote_plus
        engine = self.get_domain_engine(domain)
        host, port, user, password = self._conn_params(engine)
        db_name = self.get_db_name(domain)
        if engine == "clickhouse":
            return (
                f"clickhouse+http://{user}:{quote_plus(password)}"
                f"@{host}:{port}/{db_name}"
            )
        else:
            return (
                f"postgresql+psycopg2://{user}:{quote_plus(password)}"
                f"@{host}:{port}/{db_name}"
                f"?sslmode=disable"
            )

@lru_cache
def get_settings() -> Settings:
    # Return a singleton Settings instance (not the class itself)
    return Settings()