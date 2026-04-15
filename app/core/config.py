from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):

    # ─────────────────────────────
    # DATABASE
    # ─────────────────────────────
    DATABASE_URL: str

    # ─────────────────────────────
    # JWT CONFIG (RAILWAY SAFE)
    # ─────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ─────────────────────────────
    # OPTIONAL DEFAULTS (SAFE)
    # ─────────────────────────────
    PROJECT_NAME: str = "SmartWell API"

    # ─────────────────────────────
    # FIX POSTGRES COMPATIBILITY
    # ─────────────────────────────
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres(cls, v: str):
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # ─────────────────────────────
    # ENV LOADING
    # ─────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",   # local only (Railway ignores this)
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()