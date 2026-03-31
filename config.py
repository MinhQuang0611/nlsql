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
    pg_db_name: str = "nlsql"
    pg_db_user: str = "postgres"
    pg_db_password: str = ""

    ch_db_host: str = "localhost"
    ch_db_port: int = 8123
    ch_db_name: str = "nlsql"
    ch_db_user: str = "default"
    ch_db_password: str = ""

    @property
    def db_host(self) -> str:
        return self.pg_db_host if self.active_db == "postgres" else self.ch_db_host

    @property
    def db_port(self) -> int:
        return self.pg_db_port if self.active_db == "postgres" else self.ch_db_port

    @property
    def db_name(self) -> str:
        return self.pg_db_name if self.active_db == "postgres" else self.ch_db_name

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

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    sql_gen_model: str = "gpt-4o"
    embedding_model:str = "text-embedding-3-small"

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
    log_level: str = "INFO"

    qdrant_url: str = "http://localhost:63332"
    qdrant_api_key: str | None = None
    
    redis_url: str = "redis://localhost:6379"

    google_sheet_url: str = ""


    # Config cho DataBase Postgres
     
    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        if self.active_db == "clickhouse":
            native_port = 19000 if self.db_port == 18123 else self.db_port
            return (
                f"clickhouse+asynch://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{native_port}/{self.db_name}"
            )
        else:
            return (
                f"postgresql+asyncpg://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
                f"?ssl=disable"
            )

    @property
    def database_url_sync(self) -> str:
        from urllib.parse import quote_plus
        if self.active_db == "clickhouse":
            return (
                f"clickhouse+http://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:8123/{self.db_name}"
            )
        else:
            return (
                f"postgresql+psycopg2://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
                f"?sslmode=disable"
            )

@lru_cache
def get_settings() -> Settings:
    # Return a singleton Settings instance (not the class itself)
    return Settings()