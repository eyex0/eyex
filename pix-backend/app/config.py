from __future__ import annotations

import logging
import secrets
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("pix.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "πX Technologies"
    app_version: str = "0.1.0"
    app_debug: bool = False
    app_secret_key: str = "change-this-to-a-random-64-char-string"
    app_environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4173",
        "https://pix.com",
        "https://www.pix.com",
        "https://app.pix.com",
        "https://api.pix.com",
        "https://auth.pix.com",
        "https://docs.pix.com",
        "https://pix.pix0.workers.dev",
        "https://pix-ui.pix0.workers.dev",
        "https://pix-technologies.pixtech.workers.dev",
        "https://pix.com",
        "https://www.pix.com",
    ]
    enable_security_headers: bool = True

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://pix:pix_password@localhost:5432/pix"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # OpenAI / LangChain
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 4096
    openai_base_url: str | None = None

    # LangGraph
    langgraph_store_type: str = "memory"
    langgraph_checkpoint_interval: int = 5

    # AI Agent tuning
    agent_timeout_seconds: int = 60
    graph_timeout_seconds: int = 120

    # User quotas (0 = unlimited)
    chat_daily_message_limit: int = 100
    intelligence_daily_request_limit: int = 50

    # Auth
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"
    bcrypt_rounds: int = 12

    # Supabase integration
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_jwks_url: str = ""
    supabase_service_role_key: str = ""

    # OpenTelemetry
    otlp_endpoint: str = ""

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 100

    # Enterprise Architecture
    auto_scaler_min_instances: int = 2
    auto_scaler_max_instances: int = 50
    auto_scaler_scale_up_threshold: float = 0.75
    auto_scaler_scale_down_threshold: float = 0.25
    bulkhead_max_concurrent: int = 10
    bulkhead_queue_size: int = 20
    service_heartbeat_ttl: int = 30
    service_health_check_interval: int = 15

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Production hardening
    require_https: bool = False
    trusted_hosts: list[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def _parse_trusted_hosts(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value


    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Google AI (Gemini)
    google_api_key: str = ""
    google_model: str = "gemini-1.5-pro"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"

    # Cohere
    cohere_api_key: str = ""

    # AI Gateway
    ai_max_retries: int = 3
    ai_retry_base_delay: float = 1.0
    ai_rate_limit_per_minute: int = 100
    ai_cost_budget_daily: float = 50.0
    ai_enable_streaming: bool = True
    ai_enable_cost_tracking: bool = True
    ai_enable_semantic_cache: bool = True

    # Supabase
    supabase_service_role_key: str = ""

    # Agent runtime
    agent_max_concurrent: int = 10
    agent_default_timeout: int = 60

    # Event bus
    event_bus_type: str = "redis"  # redis | memory
    event_bus_stream_prefix: str = "pix:events"

    # Worker
    worker_poll_interval: int = 5
    worker_max_retries: int = 3
    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Settings:
        is_production = self.app_environment.lower() in {"production", "prod", "staging"}
        if is_production and self.app_secret_key == "change-this-to-a-random-64-char-string":
            raise ValueError(
                "APP_SECRET_KEY is using the default placeholder. "
                "Set a strong secret key before starting in production/staging."
            )
        if is_production and "pix_password" in self.database_url:
            logger.warning(
                "DATABASE_URL appears to use the default password. "
                "Change the database password before deploying to production."
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def generate_secret_key() -> str:
    """Generate a secure random secret key suitable for APP_SECRET_KEY."""
    return secrets.token_urlsafe(48)
