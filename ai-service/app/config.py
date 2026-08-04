"""Application configuration via Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based settings loaded from .env or env vars."""

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/inventory_advisor"
    environment: str = "development"
    service_token: str = "changeme-secret-token"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"
    forecast_horizon_days: int = 30
    tavily_api_key: str = "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"
    news_weight_factor: float = 0.15
    llm_api_key: str = "ollama-local"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2:latest"
    simulation_iterations: int = 1000
    batch_timeout_seconds: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()