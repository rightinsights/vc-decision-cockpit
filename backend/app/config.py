"""Application settings. All secrets come from the environment or backend/.env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 25
    max_pages: int = 200

    llm_provider: Literal["openai", "canned"] = "openai"  # canned = placeholder outputs for UI work, no key
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1"
    llm_temperature: float | None = 0.0

    agent_provider: Literal["mock", "openclaw"] = "mock"
    openclaw_gateway_url: str | None = None
    openclaw_gateway_token: str | None = None
    openclaw_agent_id: str = "main"
    openclaw_timeout_seconds: int = 300

    cors_origins: str = "http://localhost:3000"

    def resolved_upload_dir(self) -> Path:
        path = Path(self.upload_dir)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

    def resolved_database_url(self) -> str:
        """Relative sqlite paths resolve against backend/; plain postgres URLs get the psycopg driver."""
        url = self.database_url
        prefix = "sqlite:///./"
        if url.startswith(prefix):
            rel = url[len(prefix):]
            return f"sqlite:///{(BACKEND_DIR / rel).resolve().as_posix()}"
        for plain in ("postgres://", "postgresql://"):
            if url.startswith(plain):  # Replit / Supabase hand out driverless URLs
                return "postgresql+psycopg://" + url[len(plain):]
        return url

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
