from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/research_radar"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-large"
    openai_chat_model: str = "gpt-4o-mini"
    cors_allow_origins: str = "*"

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""

    medium_user_agent: str = "ai-research-radar/0.1 (+https://example.com)"
    medium_fetch_timeout_seconds: float = 20.0

    email_provider: str = "resend"
    resend_api_key: str = ""
    from_email: str = ""
    public_app_url: str = "http://localhost:3000"


settings = Settings()
