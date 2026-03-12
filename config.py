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
    db_port: int = 9000
    db_name: str = "nlsql"
    db_user: str = "default"
    db_password: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_echo: bool = False

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model:str = "text-embedding-3-small"

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "nlsql"

    app_env: str = "development"
    log_level: str = "INFO"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    
    redis_url: str = "redis://localhost:6379"


    # Config cho DataBase Postgres
     
    # @property
    # def database_url(self) -> str:
    #     from urllib.parse import quote_plus
    #     return (
    #         f"postgresql+asyncpg://{self.db_user}:{quote_plus(self.db_password)}"
    #         f"@{self.db_host}:{self.db_port}/{self.db_name}"
    #         f"?ssl=disable"
    #     )
    # @property
    # def database_url_sync(self) -> str:
    #     from urllib.parse import quote_plus
    #     return (
    #         f"postgresql+psycopg2://{self.db_user}:{quote_plus(self.db_password)}"
    #         f"@{self.db_host}:{self.db_port}/{self.db_name}"
    #         f"?sslmode=disable"
    #     )

    # Config cho Database Clickhouse


    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        native_port = 19000 if self.db_port == 18123 else self.db_port
        return (
            f"clickhouse+asynch://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{native_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"clickhouse+http://{self.db_user}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:8123/{self.db_name}"
        )

@lru_cache
def get_settings() -> Settings:
    # Return a singleton Settings instance (not the class itself)
    return Settings()