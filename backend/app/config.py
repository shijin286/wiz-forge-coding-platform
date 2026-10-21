import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:wizforge_dev@localhost:5432/wizforge"

    jwt_secret: str = "dev-only-change-me-please-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    anthropic_api_key: str = ""
    ai_enabled: bool = True
    ai_model: str = "claude-opus-5-5"
    ai_effort: str = "medium"

    # optional: raises GitHub's API limit for pull-request reviews from 60 to 5,000 requests/hour
    github_token: str = ""

    cors_origins: str = "http://localhost:5173"
    max_code_chars: int = 100_000

    @property
    def ai_configured(self) -> bool:
        """True when AI is enabled and some Claude credential is available."""
        has_key = bool(self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
                       or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        return self.ai_enabled and has_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
