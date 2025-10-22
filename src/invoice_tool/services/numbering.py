"""Invoice number generation respecting GoBD requirements."""
from __future__ import annotations

import pendulum
from sqlmodel import select

from ..db import get_session
from ..models import NumberSequence
from ..config import get_settings


def next_invoice_number(organization_id: int) -> str:
    settings = get_settings()
    prefix = f"{settings.invoice_number_prefix}{pendulum.now().format('YYYY')}"
    with get_session() as session:
        sequence = session.exec(
            select(NumberSequence).where(
                NumberSequence.organization_id == organization_id,
                NumberSequence.prefix == prefix,
                NumberSequence.sequence_type == "invoice",
            )
        ).one_or_none()
        if sequence is None:
            sequence = NumberSequence(
                organization_id=organization_id,
                prefix=prefix,
                sequence_type="invoice",
                last_number=0,
            )
            session.add(sequence)
            session.flush()
        sequence.last_number += 1
        session.add(sequence)
        session.flush()
        return f"{prefix}-{sequence.last_number:05d}"
