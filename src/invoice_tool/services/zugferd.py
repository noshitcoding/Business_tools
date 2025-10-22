"""ZUGFeRD 2.x hybrid invoice generation."""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import Optional

from .pdf import PDFDocument, generate_pdf
from .xrechnung import generate_xrechnung


@dataclass
class ZUGFeRDPackage:
    filename: str
    content: bytes
    pdf: PDFDocument


def build_zugferd(invoice, qr_png: Optional[bytes] = None) -> ZUGFeRDPackage:
    xml_content = generate_xrechnung(invoice)
    pdf_document = generate_pdf(invoice, ("zugferd-invoice.xml", xml_content), qr_png=qr_png)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(pdf_document.filename, pdf_document.content)
        archive.writestr("zugferd/xml/zugferd-invoice.xml", xml_content)
    return ZUGFeRDPackage(
        filename=f"invoice-{invoice.invoice_number}-zugferd.zip",
        content=buffer.getvalue(),
        pdf=pdf_document,
    )
