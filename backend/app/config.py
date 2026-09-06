"""Application settings. All secrets come from the environment or backend/.env."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Tests set VCDC_NO_DOTENV=1 so they never read a developer's real .env (and real keys).
_ENV_FILES = () if os.environ.get("VCDC_NO_DOTENV") else (BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env")


class Settings(BaseSettings):
    # Repo-root .env first, backend/.env overrides it. Either location works.
    model_config = SettingsConfigDict(env_file=_ENV_FILES, env_file_encoding="utf-8", extra="ignore")

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
    openclaw_agent_id: str = "default"
    openclaw_timeout_seconds: int = 300

    brave_api_key: str | None = None
    brave_result_count: int = 8  # per query; 2-3 queries per research run
    brave_timeout_seconds: int = 20

    cors_origins: str = "http://localhost:3000"

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        # A .env in the repo wins over shell/user environment variables, so a stale key left in the
        # Windows user environment cannot shadow the project's own configuration. Replit has no .env,
        # so its Secrets (environment variables) still apply there.
        return init_settings, dotenv_settings, env_settings, file_secret_settings

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
