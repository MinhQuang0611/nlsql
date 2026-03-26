from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "nlsql"
    db_user: str = "postgres"
    db_password: str = ""
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
        "SinhVien": "Khi đếm số lượng sinh viên, ưu tiên COUNT(DISTINCT ma_sinh_vien) nếu join với bảng khác để tránh trùng lặp.",
        "Diem": "Chỉ lấy điểm của lần thi cuối cùng (lan_thi = MAX(lan_thi)) hoặc điểm cao nhất nếu đề bài không yêu cầu cụ thể."
    }

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "nlsql"

    app_env: str = "development"
    log_level: str = "INFO"

    qdrant_url: str = "http://localhost:63332"
    qdrant_api_key: str | None = None
    
    redis_url: str = "redis://localhost:6379"


    # Config cho DataBase Postgres
     
    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"postgresql+asyncpg://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?ssl=disable"
        )
    @property
    def database_url_sync(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"postgresql+psycopg2://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?sslmode=disable"
        )

@lru_cache
def get_settings() -> Settings:
    # Return a singleton Settings instance (not the class itself)
    return Settings()