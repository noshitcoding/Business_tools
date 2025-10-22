"""Payment handling and reconciliation logic."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import pendulum
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..db import get_session
from ..models import Invoice, Payment
from ..schemas import PaymentCreate
from ..services.tax import compute_tax, determine_status


def register_payment(payload: PaymentCreate) -> Payment:
    with get_session() as session:
        invoice = session.get(Invoice, payload.invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        payment = Payment(
            invoice_id=payload.invoice_id,
            amount=payload.amount,
            currency=payload.currency,
            booking_date=payload.booking_date or pendulum.now("Europe/Berlin").date(),
            reference=payload.reference,
            source=payload.source,
        )
        session.add(payment)
        session.flush()
        total_paid = sum(p.amount for p in invoice.payments) + payload.amount
        determine_status(invoice, total_paid)
        session.add(invoice)
        session.refresh(payment)
        return payment


def get_open_items(organization_id: int) -> list[Invoice]:
    with get_session() as session:
        statement = (
            select(Invoice)
            .where(Invoice.organization_id == organization_id)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
            )
        )
        invoices = session.exec(statement).all()
        open_invoices = []
        for invoice in invoices:
            total_net, total_tax, _ = compute_tax(invoice.lines)
            total_paid = sum(p.amount for p in invoice.payments)
            if total_net + total_tax - total_paid > 0:
                open_invoices.append(invoice)
        return open_invoices


def reconcile_bank_transactions(transactions: Iterable[dict]) -> list[Payment]:
    """Match bank statement lines against outstanding invoices."""

    payments: list[Payment] = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    for tx in transactions:
        grouped[tx["reference"].strip().upper()].append(tx)

    with get_session() as session:
        for reference, items in grouped.items():
            invoice = session.exec(select(Invoice).where(Invoice.invoice_number == reference)).one_or_none()
            if not invoice:
                continue
            for tx in items:
                payment = Payment(
                    invoice_id=invoice.id,
                    amount=tx["amount"],
                    currency=tx.get("currency", invoice.currency),
                    booking_date=tx.get("date", pendulum.now("Europe/Berlin").date()),
                    reference=reference,
                    source=tx.get("source", "bank"),
                )
                session.add(payment)
                payments.append(payment)
            total_paid = sum(p.amount for p in invoice.payments) + sum(tx["amount"] for tx in items)
            determine_status(invoice, total_paid)
            session.add(invoice)
        session.flush()
        for payment in payments:
            session.refresh(payment)
    return payments
