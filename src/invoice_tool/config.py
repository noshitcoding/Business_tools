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
    allowed_hosts: list[str] = Field(
        default_factory=lambda: [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "rechnung-backend",
            "testserver",
        ],
        description="Whitelisted host headers accepted by the API gateway.",
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:8080",
            "http://127.0.0.1",
            "http://127.0.0.1:8080",
            "https://localhost",
            "https://localhost:8080",
            "https://127.0.0.1",
            "https://127.0.0.1:8080",
            "http://rechnung-frontend",
        ],
        description="Origins allowed to perform CORS requests.",
    )
    expose_docs: bool = Field(
        False,
        description="Expose interactive API documentation endpoints.",
    )
    force_https: bool = Field(
        False,
        description="Redirect all HTTP traffic to HTTPS.",
    )
    hsts_max_age: int = Field(
        63072000,
        description="Strict-Transport-Security max-age in seconds.",
    )
    hsts_include_subdomains: bool = Field(
        True,
        description="Append includeSubDomains to the HSTS header.",
    )
    hsts_preload: bool = Field(
        True,
        description="Append preload to the HSTS header.",
    )
    content_security_policy: str = Field(
        "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        description="Content-Security-Policy header value.",
    )
    referrer_policy: str = Field(
        "strict-origin-when-cross-origin",
        description="Referrer-Policy header value.",
    )
    permissions_policy: str = Field(
        "geolocation=(), microphone=(), camera=()",
        description="Permissions-Policy header value.",
    )

    class Config:
        env_prefix = "INVOICE_TOOL_"
        case_sensitive = False

    @validator("archive_path", "media_path", "secrets_path", pre=True)
    def _ensure_path(cls, value: Any) -> Path:
        if isinstance(value, Path):
            return value
        return Path(str(value))

    @validator("allowed_hosts", "allowed_origins", pre=True)
    def _split_comma_separated(cls, value: Any):  # type: ignore[override]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return memoized settings instance."""

    settings = Settings()
    for path in (settings.archive_path, settings.media_path, settings.secrets_path):
        path.mkdir(parents=True, exist_ok=True)
    return settings
