"""Application configuration and feature flags."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Central application configuration with sane defaults."""

    database_url: str = Field(
        "sqlite:///./invoice.db",
        description="SQLAlchemy-compatible connection string.",
    )
    archive_path: Path = Field(
        Path("storage/archive"),
        description="Root directory for immutable archive content.",
    )
    media_path: Path = Field(
        Path("storage/media"),
        description="Directory for generated PDFs and attachments.",
    )
    secrets_path: Path = Field(
        Path("storage/secrets"),
        description="Location for generated encryption keys and 2FA seeds.",
    )
    enable_vies: bool = Field(
        True,
        description="Toggle calling the live VIES service. Disabled in offline/test mode.",
    )
    demo_mode: bool = Field(
        False,
        description="When true, restricts destructive actions and exposes demo data.",
    )
    timezone: str = Field(
        "Europe/Berlin",
        description="Canonical timezone for temporal computations.",
    )
    invoice_number_prefix: str = Field(
        "INV",
        description="Default invoice number prefix.",
    )
    two_factor_issuer: str = Field(
        "InvoiceTool",
        description="Issuer name for OTP generation.",
    )

    class Config:
        env_prefix = "INVOICE_TOOL_"
        case_sensitive = False

    @validator("archive_path", "media_path", "secrets_path", pre=True)
    def _ensure_path(cls, value: Any) -> Path:
        if isinstance(value, Path):
            return value
        return Path(str(value))


@lru_cache
def get_settings() -> Settings:
    """Return memoized settings instance."""

    settings = Settings()
    for path in (settings.archive_path, settings.media_path, settings.secrets_path):
        path.mkdir(parents=True, exist_ok=True)
    return settings
