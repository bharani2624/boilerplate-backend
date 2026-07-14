"""Application settings, loaded from environment / .env."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_cors_origins_raw: str = Field(
        default="http://localhost:3000", alias="API_CORS_ORIGINS"
    )
    environment: str = Field(default="local", alias="ENVIRONMENT")

    # Database (Supabase Postgres connection string)
    database_url: str = Field(..., alias="DATABASE_URL")
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=5, alias="DB_MAX_OVERFLOW")

    # Auth
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expiry_minutes: int = Field(default=43200, alias="ACCESS_TOKEN_EXPIRY_MINUTES")  # 30 days

    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")

    class Config:
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
        return [o.strip() for o in self.api_cors_origins_raw.split(",") if o.strip()]


settings = Settings()
