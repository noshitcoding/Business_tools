"""Audit logging utilities."""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlmodel import select

from ..db import get_session
from ..models import AuditLog


def log_action(
    organization_id: int,
    user_id: Optional[int],
    entity: str,
    entity_id: str,
    action: str,
    payload: dict[str, Any],
) -> AuditLog:
    with get_session() as session:
        entry = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            payload=json.dumps(payload, ensure_ascii=False),
        )
        session.add(entry)
        session.flush()
        session.refresh(entry)
        return entry


def fetch_history(organization_id: int, entity: str, entity_id: str) -> list[AuditLog]:
    with get_session() as session:
        statement = (
            select(AuditLog)
            .where(
                AuditLog.organization_id == organization_id,
                AuditLog.entity == entity,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        return list(session.exec(statement).all())
