"""Peppol BIS 3 transport integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from ..config import get_settings


@dataclass
class PeppolResult:
    success: bool
    transmission_id: Optional[str]
    status: str


async def transmit_xrechnung(xml_payload: bytes, receiver_id: str, document_id: str) -> PeppolResult:
    """Send an invoice via Peppol using a configured Access Point."""

    settings = get_settings()
    endpoint = settings.__dict__.get("peppol_endpoint")
    if not endpoint:
        return PeppolResult(success=False, transmission_id=None, status="Peppol endpoint not configured")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            endpoint,
            json={
                "receiver": receiver_id,
                "document_id": document_id,
                "payload": xml_payload.decode("utf-8"),
            },
        )
    if response.status_code >= 400:
        return PeppolResult(success=False, transmission_id=None, status=response.text)
    data = response.json()
    return PeppolResult(success=True, transmission_id=data.get("transmission_id"), status="sent")
