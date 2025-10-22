"""Validation helpers for regulatory checks."""
from __future__ import annotations

import re
from typing import Iterable

from stdnum import iban

from ..models import Invoice


def validate_invoice_number_unique(existing_numbers: Iterable[str], candidate: str) -> None:
    if candidate in existing_numbers:
        raise ValueError("Invoice number must be unique")


def validate_iban(value: str) -> None:
    try:
        iban.validate(value)
    except Exception as exc:  # pragma: no cover - stdnum raises different errors
        raise ValueError("Invalid IBAN") from exc


def ensure_reverse_charge_text(invoice: Invoice) -> str:
    if invoice.reverse_charge:
        return "Steuerschuldnerschaft des Leistungsempfängers (§ 13b UStG)."
    if invoice.self_billing:
        return "Gutschrift gemäß § 14 Abs. 2 Satz 2 UStG."
    return invoice.tax_exemption_text or ""
