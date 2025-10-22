"""Invoice related API endpoints."""
from __future__ import annotations

import base64

import pendulum
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..db import get_session
from ..models import Invoice, InvoiceLine, Organization, Customer
from ..schemas import (
    EPCQRCodeRequest,
    EPCQRCodeResponse,
    InvoiceCreate,
    InvoiceRead,
    PaymentCreate,
    PaymentRead,
)
from ..services import payments
from ..services.epc_qr import generate_epc_qr
from ..services.numbering import next_invoice_number
from ..services.pdf import generate_pdf
from ..services.tax import compute_tax
from ..services.validators import validate_invoice_number_unique
from ..services.xrechnung import generate_xrechnung
from ..services.zugferd import build_zugferd

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _load_invoice(session: Session, invoice_id: int) -> Invoice | None:
    statement = (
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.lines),
            selectinload(Invoice.issuer),
            selectinload(Invoice.customer),
            selectinload(Invoice.payments),
        )
    )
    return session.exec(statement).one_or_none()


def _invoice_to_schema(invoice: Invoice) -> InvoiceRead:
    total_net, total_tax, _ = compute_tax(invoice.lines)
    return InvoiceRead(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        type=invoice.type,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        total_net=total_net,
        total_tax=total_tax,
        total_gross=total_net + total_tax,
        currency=invoice.currency,
        reverse_charge=invoice.reverse_charge,
        self_billing=invoice.self_billing,
        created_at=invoice.created_at,
    )


@router.post("", response_model=InvoiceRead)
def create_invoice(payload: InvoiceCreate) -> InvoiceRead:
    with get_session() as session:
        organization = session.get(Organization, payload.organization_id)
        customer = session.get(Customer, payload.customer_id)
        if not organization or not customer:
            raise HTTPException(status_code=400, detail="Invalid organization or customer")
        if payload.invoice_number:
            existing_numbers = session.exec(
                select(Invoice.invoice_number).where(Invoice.organization_id == payload.organization_id)
            ).all()
            validate_invoice_number_unique(existing_numbers, payload.invoice_number)
            invoice_number = payload.invoice_number
        else:
            invoice_number = next_invoice_number(payload.organization_id)
        invoice = Invoice(
            organization_id=payload.organization_id,
            customer_id=payload.customer_id,
            invoice_number=invoice_number,
            type=payload.type,
            status=payload.status,
            issue_date=payload.issue_date or pendulum.now("Europe/Berlin").date(),
            service_period_start=payload.service_period_start,
            service_period_end=payload.service_period_end,
            currency=payload.currency,
            exchange_rate=payload.exchange_rate,
            reverse_charge=payload.reverse_charge,
            self_billing=payload.self_billing,
            tax_exemption_text=payload.tax_exemption_text,
            payment_terms=payload.payment_terms.json() if payload.payment_terms else None,
            due_date=payload.due_date,
            base_document_number=payload.base_document_number,
            notes=payload.notes,
        )
        session.add(invoice)
        session.flush()
        for line_payload in payload.lines:
            line = InvoiceLine(
                invoice_id=invoice.id,
                description=line_payload.description,
                quantity=line_payload.quantity,
                unit=line_payload.unit,
                net_amount=line_payload.net_amount,
                tax_category=line_payload.tax_category,
                tax_rate=line_payload.tax_rate,
            )
            session.add(line)
        session.flush()
        invoice = _load_invoice(session, invoice.id)
        if invoice is None:
            raise HTTPException(status_code=500, detail="Failed to load invoice")
        return _invoice_to_schema(invoice)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int) -> InvoiceRead:
    with get_session() as session:
        invoice = _load_invoice(session, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return _invoice_to_schema(invoice)


@router.post("/{invoice_id}/pdf")
def generate_invoice_pdf(invoice_id: int) -> Response:
    with get_session() as session:
        invoice = _load_invoice(session, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        structured = (f"invoice-{invoice.invoice_number}.xml", generate_xrechnung(invoice))
        qr_png = None
        if invoice.issuer.iban:
            totals = compute_tax(invoice.lines)
            qr_payload = generate_epc_qr(
                EPCQRCodeRequest(
                    name=invoice.issuer.name,
                    iban=invoice.issuer.iban,
                    bic=invoice.issuer.bic,
                    amount=totals[0] + totals[1],
                    remittance_information=f"Rechnung {invoice.invoice_number}",
                )
            )
            qr_png = qr_payload.png
        pdf = generate_pdf(invoice, structured_attachment=structured, qr_png=qr_png)
        return StreamingResponse(
            iter([pdf.content]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={pdf.filename}"},
        )


@router.post("/{invoice_id}/xrechnung")
def generate_invoice_xrechnung(invoice_id: int) -> Response:
    with get_session() as session:
        invoice = _load_invoice(session, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        xml = generate_xrechnung(invoice)
        return StreamingResponse(iter([xml]), media_type="application/xml", headers={"Content-Disposition": f"attachment; filename=invoice-{invoice.invoice_number}.xml"})


@router.post("/{invoice_id}/zugferd")
def generate_invoice_zugferd(invoice_id: int) -> Response:
    with get_session() as session:
        invoice = _load_invoice(session, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        package = build_zugferd(invoice)
        return StreamingResponse(iter([package.content]), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={package.filename}"})


@router.post("/{invoice_id}/payments", response_model=PaymentRead)
def create_payment(invoice_id: int, payload: PaymentCreate) -> PaymentRead:
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        amount=payload.amount,
        currency=payload.currency,
        booking_date=payload.booking_date,
        reference=payload.reference,
        source=payload.source,
    )
    payment = payments.register_payment(payment_data)
    return PaymentRead(
        id=payment.id,
        invoice_id=payment.invoice_id,
        amount=payment.amount,
        currency=payment.currency,
        booking_date=payment.booking_date,
        created_at=payment.created_at,
    )


@router.get("/open", response_model=list[InvoiceRead])
def list_open_items(organization_id: int) -> list[InvoiceRead]:
    invoices = payments.get_open_items(organization_id)
    return [_invoice_to_schema(inv) for inv in invoices]


@router.post("/epc", response_model=EPCQRCodeResponse)
def create_epc_qr(payload: EPCQRCodeRequest) -> EPCQRCodeResponse:
    qr = generate_epc_qr(payload)
    return EPCQRCodeResponse(
        payload=qr.payload,
        svg=qr.svg,
        png_base64=base64.b64encode(qr.png).decode("ascii"),
    )
