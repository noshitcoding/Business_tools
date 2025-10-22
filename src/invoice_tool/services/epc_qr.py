"""Generate EPC QR codes for SEPA credit transfer."""
from __future__ import annotations

import io
from dataclasses import dataclass

import segno

from ..schemas import EPCQRCodeRequest


@dataclass
class EPCPayload:
    payload: str
    svg: str
    png: bytes


def generate_epc_qr(data: EPCQRCodeRequest) -> EPCPayload:
    payload = "\n".join(
        [
            "BCD",
            "002",
            data.version,
            "SCT",
            "",
            data.name[:70],
            data.iban.replace(" ", "").upper(),
            (data.bic or "").upper(),
            f"EUR{data.amount:.2f}",
            data.purpose or "",
            "",
            data.remittance_information,
        ]
    )
    qr = segno.make(payload, error="M")
    buffer = io.StringIO()
    qr.save(buffer, kind="svg", xmldecl=False)
    svg_payload = buffer.getvalue()
    png_buffer = io.BytesIO()
    qr.save(png_buffer, kind="png", scale=5)
    return EPCPayload(payload=payload, svg=svg_payload, png=png_buffer.getvalue())
