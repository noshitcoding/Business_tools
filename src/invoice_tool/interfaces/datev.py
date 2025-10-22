"""DATEV / SKR export helpers."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Iterable

from ..models import Invoice
from ..services.tax import compute_tax


@dataclass
class DATEVExport:
    filename: str
    content: bytes


def export_invoices(invoices: Iterable[Invoice]) -> DATEVExport:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Buchungstext", "Belegfeld1", "Sollkonto", "Habenkonto", "Betrag", "Steuersatz"])
    for invoice in invoices:
        total_net, total_tax, _ = compute_tax(invoice.lines)
        writer.writerow(
            [
                f"Rechnung {invoice.invoice_number}",
                invoice.invoice_number,
                "8400",  # Umsatzsteuer 19%
                "10000",
                f"{total_net + total_tax:.2f}",
                "19" if total_tax else "0",
            ]
        )
    return DATEVExport(
        filename="datev-export.csv",
        content=buffer.getvalue().encode("latin-1", errors="ignore"),
    )
