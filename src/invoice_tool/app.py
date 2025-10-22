"""FastAPI application wiring for the invoice tool."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from .config import Settings, get_settings
from .db import init_db
from .routers import compliance, invoices, reporting, users
from .security import SecurityHeadersMiddleware

settings = get_settings()

def _build_strict_transport_security(config: Settings) -> str | None:
    """Return the Strict-Transport-Security header value if enabled."""

    if config.hsts_max_age <= 0:
        return None
    directives: list[str] = [f"max-age={config.hsts_max_age}"]
    if config.hsts_include_subdomains:
        directives.append("includeSubDomains")
    if config.hsts_preload:
        directives.append("preload")
    return "; ".join(directives)


fastapi_kwargs: dict[str, str | None] = {}
if not settings.expose_docs:
    fastapi_kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

app = FastAPI(
    title="Invoice Tool",
    description="Rechnungsplattform mit EN 16931, GoBD und DSGVO-Konformität.",
    version="0.1.0",
    **fastapi_kwargs,
)

if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Authorization",
        "Content-Type",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
    expose_headers=["Content-Disposition"],
    allow_credentials=False,
    max_age=86400,
)

app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy=settings.content_security_policy,
    referrer_policy=settings.referrer_policy,
    permissions_policy=settings.permissions_policy,
    strict_transport_security=_build_strict_transport_security(settings),
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(reporting.router)
app.include_router(compliance.router)
