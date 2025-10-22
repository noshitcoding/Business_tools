"""Compliance endpoints (VAT validation, archive)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from ..schemas import VATValidationResponse
from ..services.archive import fetch_document
from ..services.vies import validate_vat

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/vat-id/{vat_id}", response_model=VATValidationResponse)
async def validate_vat_number(vat_id: str) -> VATValidationResponse:
    if len(vat_id) < 4:
        raise HTTPException(status_code=400, detail="VAT ID too short")
    result = await validate_vat(vat_id)
    return VATValidationResponse(
        vat_id=vat_id,
        valid=result.valid,
        trader_name=result.trader_name,
        trader_address=result.trader_address,
        consultation_number=result.consultation_number,
        checked_at=result.checked_at,
    )


@router.get("/archive/{entry_id}")
def download_archive_document(entry_id: int) -> Response:
    content = fetch_document(entry_id)
    return Response(content=content, media_type="application/octet-stream")
