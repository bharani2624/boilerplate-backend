"""Application settings, loaded from environment / .env.

Why this file exists: every other module imports the single `settings` object from
here instead of calling os.getenv() directly. That keeps env-var names and defaults
in one place, and pydantic validates them at startup (fail fast if DATABASE_URL or
JWT_SECRET_KEY is missing, instead of failing on the first request).
"""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API — host/port for uvicorn, CORS origins for the frontend calling this API.
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    # Raw comma-separated string, not list[str]: pydantic-settings tries to JSON-parse
    # list-typed env vars before our code runs, which breaks on a plain "http://a,http://b"
    # value. Kept as str here and exposed as a list via the api_cors_origins property below.
    api_cors_origins_raw: str = Field(
        default="http://localhost:3000", alias="API_CORS_ORIGINS"
    )
    environment: str = Field(default="local", alias="ENVIRONMENT")

    # Database — the Supabase Postgres connection string, plus SQLAlchemy pool sizing.
    database_url: str = Field(..., alias="DATABASE_URL")
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=5, alias="DB_MAX_OVERFLOW")

    # Auth — secret used to sign/verify our own session JWTs (see src/services/auth_service.py).
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expiry_minutes: int = Field(default=43200, alias="ACCESS_TOKEN_EXPIRY_MINUTES")  # 30 days

    # The Google OAuth Web client ID that ID tokens must have been issued for
    # (checked in verify_google_id_token so a token minted for a different app is rejected).
    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")

    class Config:
        # Loads variables from a .env file at the repo root in addition to real env vars —
        # real env vars (e.g. set by Render) still win if both are present.
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        case_sensitive = False
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Normalize to the psycopg3 driver regardless of what scheme was pasted
        # (Supabase gives you plain postgresql://).
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg://", 1)

    @property
    def api_cors_origins(self) -> list[str]:
        """List form of api_cors_origins_raw, for passing straight to CORSMiddleware."""
        return [o.strip() for o in self.api_cors_origins_raw.split(",") if o.strip()]


# Instantiated once at import time — every module does `from config.settings import settings`
# and gets this same validated instance, rather than re-reading env vars everywhere.
settings = Settings()
