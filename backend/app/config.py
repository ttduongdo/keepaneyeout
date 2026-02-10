from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/research_radar"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-large"
    openai_chat_model: str = "gpt-4o-mini"
    cors_allow_origins: str = "*"


settings = Settings()
