from __future__ import annotations

import base64
import importlib
import os
import tempfile

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import invoice_tool.app as app_module
from invoice_tool.config import get_settings
from invoice_tool.db import get_session, init_db
from invoice_tool.models import Customer, InvoiceStatus, Organization, TaxCategory


def setup_module(module):
    tmpdir = tempfile.mkdtemp()
    os.environ["INVOICE_TOOL_DATABASE_URL"] = f"sqlite:///{tmpdir}/test.db"
    get_settings.cache_clear()  # type: ignore[attr-defined]
    importlib.reload(app_module)
    init_db()
    with get_session() as session:
        org = Organization(
            name="Muster GmbH",
            street="Hauptstr. 1",
            postal_code="12345",
            city="Berlin",
            country="DE",
            vat_id="DE123456789",
            tax_number="11/222/33333",
            iban="DE12500105170648489890",
            bic="INGDDEFFXXX",
        )
        session.add(org)
        session.flush()
        customer = Customer(
            organization_id=org.id,
            name="Beispiel AG",
            street="Nebenweg 5",
            postal_code="54321",
            city="München",
            country="DE",
            vat_id="DE987654321",
        )
        session.add(customer)


def test_invoice_lifecycle():
    client = TestClient(app_module.app)
    invoice_payload = {
        "organization_id": 1,
        "customer_id": 1,
        "lines": [
            {
                "description": "Beratung",
                "quantity": 5,
                "unit": "h",
                "net_amount": 100,
                "tax_category": TaxCategory.STANDARD.value,
                "tax_rate": 0.19,
            }
        ],
        "reverse_charge": False,
    }
    response = client.post("/invoices", json=invoice_payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == InvoiceStatus.DRAFT.value
    invoice_id = data["id"]

    pdf_response = client.post(f"/invoices/{invoice_id}/pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")

    xml_response = client.post(f"/invoices/{invoice_id}/xrechnung")
    assert xml_response.status_code == 200
    assert xml_response.headers["content-type"].startswith("application/xml")

    qr_response = client.post(
        "/invoices/epc",
        json={
            "name": "Muster GmbH",
            "iban": "DE12500105170648489890",
            "bic": "INGDDEFFXXX",
            "amount": 100.0,
            "remittance_information": "Test",
        },
    )
    assert qr_response.status_code == 200
    payload = qr_response.json()
    base64.b64decode(payload["png_base64"])  # should decode without error
