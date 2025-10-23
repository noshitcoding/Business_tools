"""Tax calculation utilities covering German VAT rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pendulum

from ..config import get_settings
from ..models import Invoice, InvoiceLine, TaxCategory


@dataclass
class TaxBreakdown:
    category: TaxCategory
    base: float
    rate: float
    tax: float


def compute_tax(lines: Iterable[InvoiceLine]) -> tuple[float, float, list[TaxBreakdown]]:
    total_net = 0.0
    total_tax = 0.0
    breakdown: dict[tuple[TaxCategory, float], TaxBreakdown] = {}

    for line in lines:
        base = line.net_amount * line.quantity
        total_net += base
        rate = line.tax_rate if line.tax_category not in {
            TaxCategory.REVERSE_CHARGE,
            TaxCategory.EU_SUPPLY,
            TaxCategory.EXPORT,
            TaxCategory.ZERO,
        } else 0.0
        tax_amount = base * rate
        total_tax += tax_amount
        key = (line.tax_category, line.tax_rate)
        if key not in breakdown:
            breakdown[key] = TaxBreakdown(line.tax_category, 0.0, line.tax_rate, 0.0)
        entry = breakdown[key]
        entry.base += base
        entry.tax += tax_amount

    return total_net, total_tax, list(breakdown.values())


def determine_status(invoice: Invoice, total_paid: float) -> None:
    if invoice.status == invoice.status.CANCELLED:
        return
    if total_paid <= 0:
        invoice.status = invoice.status.APPROVED if invoice.status != invoice.status.DRAFT else invoice.status.DRAFT
        return
    total_net, total_tax, _ = compute_tax(invoice.lines)
    outstanding = total_net + total_tax - total_paid
    today = pendulum.now(get_settings().timezone).date()
    if outstanding <= 0:
        invoice.status = invoice.status.PAID
    elif invoice.due_date and outstanding > 0 and invoice.due_date < today:
        invoice.status = invoice.status.OVERDUE
    elif outstanding < total_net + total_tax:
        invoice.status = invoice.status.PARTLY_PAID
