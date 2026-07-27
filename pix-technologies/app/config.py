from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "DEBUG"

    # Application
    app_name: str = "EyeX Technologies"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # PostgreSQL
    postgres_server: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "pix"
    postgres_password: str = "pix_secret"
    postgres_db: str = "pix"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.0

    # LangChain
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "pix-technologies"

    # Security
    secret_key: str = "change-this-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database Pool
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False


settings = Settings()
