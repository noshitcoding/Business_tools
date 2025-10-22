"""PDF/A oriented invoice renderer."""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfdoc
from reportlab.pdfgen import canvas

from ..config import get_settings
from ..models import Invoice
from ..services.tax import TaxBreakdown, compute_tax
from ..services.validators import ensure_reverse_charge_text


@dataclass
class PDFDocument:
    filename: str
    content: bytes


def _load_icc_profile() -> Optional[bytes]:
    settings = get_settings()
    candidates = [
        Path(__file__).with_name("sRGB.icc"),
        settings.secrets_path / "sRGB.icc",
    ]
    for path in candidates:
        if path.exists():
            return path.read_bytes()
    return None


def _apply_pdfa_metadata(pdf: canvas.Canvas, invoice: Invoice, icc_profile: Optional[bytes]) -> None:
    doc = pdf._doc  # type: ignore[attr-defined]
    doc.setLang("de-DE")
    info = doc.info
    info.title = f"Rechnung {invoice.invoice_number}"
    info.author = invoice.issuer.name
    info.subject = "Rechnung gemäß § 14 UStG"
    info.creator = "Invoice Tool"
    info.keywords = "Rechnung, EN 16931, XRechnung, ZUGFeRD"
    xmp = f"""<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>
    <x:xmpmeta xmlns:x='adobe:ns:meta/'>
      <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
        <rdf:Description rdf:about='' xmlns:pdfaid='http://www.aiim.org/pdfa/ns/id/'>
          <pdfaid:part>3</pdfaid:part>
          <pdfaid:conformance>B</pdfaid:conformance>
        </rdf:Description>
        <rdf:Description rdf:about='' xmlns:dc='http://purl.org/dc/elements/1.1/'>
          <dc:title><rdf:Alt><rdf:li xml:lang='x-default'>Rechnung {invoice.invoice_number}</rdf:li></rdf:Alt></dc:title>
          <dc:creator><rdf:Seq><rdf:li>{invoice.issuer.name}</rdf:li></rdf:Seq></dc:creator>
          <dc:description><rdf:Alt><rdf:li xml:lang='x-default'>Rechnung gemäß § 14 UStG</rdf:li></rdf:Alt></dc:description>
        </rdf:Description>
      </rdf:RDF>
    </x:xmpmeta>
    <?xpacket end='w'?>"""
    doc.setXMPMetadata(xmp)
    if icc_profile:
        intent = pdfdoc.PDFOutputIntent(
            subType="GTS_PDFA1",
            outputCondition="sRGB IEC61966-2.1",
            outputConditionIdentifier="sRGB IEC61966-2.1",
            registryName="http://www.color.org",
            info="sRGB IEC61966-2.1",
            destOutputProfile=icc_profile,
        )
        doc.addOutputIntent(intent)


def _draw_header(pdf: canvas.Canvas, invoice: Invoice) -> None:
    width, height = A4
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(20 * mm, height - 25 * mm, invoice.issuer.name)
    pdf.setFont("Helvetica", 10)
    y = height - 35 * mm
    issuer_lines = [
        invoice.issuer.street,
        f"{invoice.issuer.postal_code} {invoice.issuer.city}",
        f"{invoice.issuer.country}",
    ]
    if invoice.issuer.vat_id:
        issuer_lines.append(f"USt-IdNr.: {invoice.issuer.vat_id}")
    if invoice.issuer.tax_number:
        issuer_lines.append(f"Steuernummer: {invoice.issuer.tax_number}")
    if invoice.issuer.email:
        issuer_lines.append(invoice.issuer.email)
    for line in issuer_lines:
        pdf.drawString(20 * mm, y, line)
        y -= 5 * mm

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(120 * mm, height - 25 * mm, "Rechnung")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(120 * mm, height - 32 * mm, f"Rechnungsnummer: {invoice.invoice_number}")
    pdf.drawString(120 * mm, height - 37 * mm, f"Rechnungsdatum: {invoice.issue_date.isoformat()}")
    if invoice.service_period_start and invoice.service_period_end:
        pdf.drawString(
            120 * mm,
            height - 42 * mm,
            f"Leistungszeitraum: {invoice.service_period_start.isoformat()} - {invoice.service_period_end.isoformat()}",
        )
    elif invoice.service_period_start:
        pdf.drawString(120 * mm, height - 42 * mm, f"Leistungsdatum: {invoice.service_period_start.isoformat()}")
    pdf.drawString(120 * mm, height - 47 * mm, f"Fällig bis: {invoice.due_date.isoformat() if invoice.due_date else 'siehe Zahlungsbedingungen'}")

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(20 * mm, height - 70 * mm, invoice.customer.name)
    pdf.setFont("Helvetica", 10)
    customer_lines = [
        invoice.customer.street,
        f"{invoice.customer.postal_code} {invoice.customer.city}",
        invoice.customer.country,
    ]
    if invoice.customer.vat_id:
        customer_lines.append(f"USt-IdNr.: {invoice.customer.vat_id}")
    offset = 75 * mm
    for line in customer_lines:
        pdf.drawString(20 * mm, height - offset, line)
        offset += 5 * mm


def _draw_lines(pdf: canvas.Canvas, invoice: Invoice, breakdown: Iterable[TaxBreakdown]) -> float:
    width, height = A4
    y = height - 100 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(20 * mm, y, "Pos")
    pdf.drawString(35 * mm, y, "Beschreibung")
    pdf.drawString(120 * mm, y, "Menge")
    pdf.drawString(140 * mm, y, "Netto")
    pdf.drawString(160 * mm, y, "Steuersatz")
    pdf.drawString(180 * mm, y, "Betrag")
    pdf.setFont("Helvetica", 10)
    y -= 6 * mm
    for idx, line in enumerate(invoice.lines, start=1):
        base = line.net_amount * line.quantity
        pdf.drawString(20 * mm, y, str(idx))
        pdf.drawString(35 * mm, y, line.description)
        pdf.drawRightString(135 * mm, y, f"{line.quantity:.2f} {line.unit}")
        pdf.drawRightString(155 * mm, y, f"{base:.2f}")
        pdf.drawRightString(175 * mm, y, f"{line.tax_rate * 100:.0f}%")
        pdf.drawRightString(200 * mm, y, f"{base * line.tax_rate:.2f}")
        y -= 6 * mm
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(35 * mm, y, "Steuerübersicht")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    for entry in breakdown:
        pdf.drawString(35 * mm, y, f"{entry.category.value} ({entry.rate * 100:.0f}%)")
        pdf.drawRightString(155 * mm, y, f"{entry.base:.2f}")
        pdf.drawRightString(200 * mm, y, f"{entry.tax:.2f}")
        y -= 5 * mm
    total_net, total_tax, _ = compute_tax(invoice.lines)
    total_gross = total_net + total_tax
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(155 * mm, y, "Netto")
    pdf.drawRightString(200 * mm, y, f"{total_net:.2f} {invoice.currency}")
    y -= 5 * mm
    pdf.drawRightString(155 * mm, y, "Steuer")
    pdf.drawRightString(200 * mm, y, f"{total_tax:.2f} {invoice.currency}")
    y -= 5 * mm
    pdf.drawRightString(155 * mm, y, "Brutto")
    pdf.drawRightString(200 * mm, y, f"{total_gross:.2f} {invoice.currency}")
    return y - 10 * mm


def _draw_footer(pdf: canvas.Canvas, invoice: Invoice, y: float, qr_png: Optional[bytes]) -> None:
    if qr_png:
        from reportlab.lib.utils import ImageReader

        img = ImageReader(io.BytesIO(qr_png))
        pdf.drawImage(img, 20 * mm, y - 40 * mm, width=35 * mm, height=35 * mm, mask="auto")
        pdf.setFont("Helvetica", 8)
        pdf.drawString(20 * mm, y - 45 * mm, "EPC-QR-Code für SEPA-Überweisung")
    pdf.setFont("Helvetica", 9)
    text = pdf.beginText(65 * mm, y - 5 * mm)
    payment_lines = [
        f"Bitte überweisen Sie den Rechnungsbetrag bis {invoice.due_date.isoformat() if invoice.due_date else 'zum angegebenen Termin'}.",
    ]
    if invoice.issuer.iban:
        payment_lines.append(f"IBAN: {invoice.issuer.iban}")
    if invoice.issuer.bic:
        payment_lines.append(f"BIC: {invoice.issuer.bic}")
    payment_lines.append(ensure_reverse_charge_text(invoice))
    if invoice.notes:
        payment_lines.append(invoice.notes)
    for line in payment_lines:
        if not line:
            continue
        text.textLine(line)
    pdf.drawText(text)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(20 * mm, 15 * mm, "Dieses Dokument wurde elektronisch erstellt und ist ohne Unterschrift gültig.")
    pdf.drawString(20 * mm, 10 * mm, "Archivierung gemäß GoBD erfolgt im strukturierten Datensatz.")


def generate_pdf(invoice: Invoice, structured_attachment: Optional[tuple[str, bytes]] = None, qr_png: Optional[bytes] = None) -> PDFDocument:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    icc = _load_icc_profile()
    _apply_pdfa_metadata(pdf, invoice, icc)
    breakdown = compute_tax(invoice.lines)[2]
    _draw_header(pdf, invoice)
    y = _draw_lines(pdf, invoice, breakdown)
    _draw_footer(pdf, invoice, y, qr_png)
    if structured_attachment:
        filename, payload = structured_attachment
        pdf._doc.addAttachment(
            filename,
            payload,
            fileName=filename,
            desc="EN 16931 Strukturdatensatz",
            AFRelationship="Data",
        )
    pdf.showPage()
    pdf.save()
    return PDFDocument(
        filename=f"invoice-{invoice.invoice_number}.pdf",
        content=buffer.getvalue(),
    )
