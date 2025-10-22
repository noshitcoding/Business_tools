"""VIES VAT number validation service."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
import pendulum
from lxml import etree

from ..config import get_settings

VIES_ENDPOINT = "https://ec.europa.eu/taxation_customs/vies/services/checkVatService"


@dataclass
class VIESResult:
    vat_id: str
    valid: bool
    trader_name: Optional[str]
    trader_address: Optional[str]
    consultation_number: Optional[str]
    checked_at: datetime


async def validate_vat(vat_id: str) -> VIESResult:
    settings = get_settings()
    now = pendulum.now("UTC")
    if not settings.enable_vies:
        return VIESResult(vat_id=vat_id, valid=True, trader_name=None, trader_address=None, consultation_number=None, checked_at=now)

    country_code = vat_id[:2]
    number = vat_id[2:]
    envelope = f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <checkVat xmlns="urn:ec.europa.eu:taxud:vies:services:checkVat:types">
              <countryCode>{country_code}</countryCode>
              <vatNumber>{number}</vatNumber>
            </checkVat>
          </soap:Body>
        </soap:Envelope>
    """.strip()

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            VIES_ENDPOINT,
            data=envelope,
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": ""
            },
        )
        response.raise_for_status()

    xml = etree.fromstring(response.content)
    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns": "urn:ec.europa.eu:taxud:vies:services:checkVat:types",
    }
    body = xml.find("soap:Body", ns)
    check_vat_response = body[0]
    valid = check_vat_response.findtext("ns:valid", namespaces=ns) == "true"
    name = check_vat_response.findtext("ns:name", namespaces=ns)
    address = check_vat_response.findtext("ns:address", namespaces=ns)
    consultation_number = check_vat_response.findtext("ns:requestIdentifier", namespaces=ns)
    return VIESResult(
        vat_id=vat_id,
        valid=valid,
        trader_name=name,
        trader_address=address,
        consultation_number=consultation_number,
        checked_at=now,
    )


def validate_vat_sync(vat_id: str) -> VIESResult:
    return asyncio.get_event_loop().run_until_complete(validate_vat(vat_id))
