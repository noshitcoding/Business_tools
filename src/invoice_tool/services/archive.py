"""Revisionssichere Archivierung gemäß GoBD."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Optional

from ..config import get_settings
from ..db import get_session
from ..models import ArchiveEntry


def store_document(
    organization_id: int,
    invoice_id: Optional[int],
    filename: str,
    content: bytes,
    mime_type: str,
    document_type: str,
    valid_until: Optional[date] = None,
) -> ArchiveEntry:
    settings = get_settings()
    digest = hashlib.sha256(content).hexdigest()
    storage_path = settings.archive_path / digest[:2] / digest
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    if not storage_path.exists():
        storage_path.write_bytes(content)
    with get_session() as session:
        entry = ArchiveEntry(
            organization_id=organization_id,
            invoice_id=invoice_id,
            filename=filename,
            storage_path=str(storage_path.relative_to(settings.archive_path)),
            sha256=digest,
            mime_type=mime_type,
            document_type=document_type,
            valid_until=valid_until,
        )
        session.add(entry)
        session.flush()
        session.refresh(entry)
        return entry


def fetch_document(entry_id: int) -> bytes:
    settings = get_settings()
    with get_session() as session:
        entry = session.get(ArchiveEntry, entry_id)
        if not entry:
            raise ValueError("Archive entry not found")
    path = settings.archive_path / entry.storage_path
    return path.read_bytes()
