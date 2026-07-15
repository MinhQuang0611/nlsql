from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    active_db: str = "postgres"

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


    @property
    def db_host(self) -> str:
        return self.pg_db_host if self.active_db == "postgres" else self.ch_db_host

    @property
    def db_port(self) -> int:
        return self.pg_db_port if self.active_db == "postgres" else self.ch_db_port

    def get_db_name(self, domain: str = "qldt") -> str:
        if self.active_db == "postgres":
            return self.pg_db_name_qldt if domain == "qldt" else self.pg_db_name_tcns
        return self.ch_db_name_qldt if domain == "qldt" else self.ch_db_name_tcns

    @property
    def db_user(self) -> str:
        return self.pg_db_user if self.active_db == "postgres" else self.ch_db_user

    @property
    def db_password(self) -> str:
        return self.pg_db_password if self.active_db == "postgres" else self.ch_db_password
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_echo: bool = False

    # LLM - OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Per-agent model configuration
    openai_model: str = "gpt-4o-mini"        # intent, answer, chart, knowledge, schema, sql_check, sql_plan agents
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

    PREDEFINED_FORMULAS: dict[str, str] = {
        "ty_le_dat": "ROUND((SUM(CASE WHEN diem >= 4.0 THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 2)",
        "diem_trung_binh": "ROUND(AVG(diem), 2)"
    }
    
    TABLE_RULES: dict[str, str] = {
        "SinhVien": "Khi đếm số lượng sinh viên, ưu tiên COUNT(DISTINCT ma_sinh_vien) nếu join với bảng khác để tránh trùng lặp. Khi được hỏi về 'ngành học' của sinh viên, KHÔNG JOIN với bảng KhoaNganh, mà phải JOIN với bảng Nganh thông qua maNganh.",
        "Nganh": "Bảng đại diện cho ngành học. Khi câu hỏi hỏi về 'Ngành', 'Ngành học' (ví dụ top 5 ngành), luôn dùng bảng Nganh và không nhầm lẫn với bảng KhoaNganh.",
        "KhoaNganh": "CHỈ dùng bảng này khi câu hỏi NHẮC CỤ THỂ đến Khoa (Department). Nếu hỏi về ngành (Major), hãy dùng bảng Nganh.",
        "Diem": "Chỉ lấy điểm của lần thi cuối cùng (lan_thi = MAX(lan_thi)) hoặc điểm cao nhất nếu đề bài không yêu cầu cụ thể.",
        "KqhtTichLuy": "Khi người dùng hỏi về điểm GPA hoặc điểm tích lũy hệ số 4 (ví dụ > 3.6), phải sử dụng cột `trungBinhThang4`. Chỉ dùng cột `trungBinh` khi nói về điểm hệ số 10."
    }

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "nlsql"

    app_env: str = "development"
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
        if self.active_db == "clickhouse":
            native_port = 19000 if self.db_port == 18123 else self.db_port
            return (
                f"clickhouse+asynch://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{native_port}/{self.get_db_name(domain)}"
            )
        else:
            return (
                f"postgresql+asyncpg://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{self.db_port}/{self.get_db_name(domain)}"
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
        if self.active_db == "clickhouse":
            return (
                f"clickhouse+http://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{self.db_port}/{self.get_db_name(domain)}"
            )
        else:
            return (
                f"postgresql+psycopg2://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{self.db_port}/{self.get_db_name(domain)}"
                f"?sslmode=disable"
            )

@lru_cache
def get_settings() -> Settings:
    # Return a singleton Settings instance (not the class itself)
    return Settings()