from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://radar_user:radar@localhost:5432/research_radar"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-large"
    openai_chat_model: str = "gpt-4o-mini"
    frontend_url: str = "http://localhost:3000"

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""

    medium_user_agent: str = "ai-research-radar/0.1 (+https://example.com)"
    medium_fetch_timeout_seconds: float = 20.0

    email_provider: str = "resend"
    resend_api_key: str = ""
    from_email: str = ""
    public_app_url: str = "http://localhost:3000"

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 60 * 15

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/oauth/google"


settings = Settings()
