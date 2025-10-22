"""FastAPI application wiring for the invoice tool."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import compliance, invoices, reporting, users

settings = get_settings()

app = FastAPI(
    title="Invoice Tool",
    description="Rechnungsplattform mit EN 16931, GoBD und DSGVO-Konformität.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
