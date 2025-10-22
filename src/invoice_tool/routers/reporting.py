"""Reporting endpoints for VAT and KPIs."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..db import get_session
from ..models import Invoice
from ..schemas import OSSReport, ReportRequest, VATReturnSummary
from ..services.tax import compute_tax

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/vat-return", response_model=VATReturnSummary)
def vat_return(organization_id: int, payload: ReportRequest) -> VATReturnSummary:
    with get_session() as session:
        statement = (
            select(Invoice)
            .where(
                Invoice.organization_id == organization_id,
                Invoice.issue_date >= payload.start_date,
                Invoice.issue_date <= payload.end_date,
            )
            .options(selectinload(Invoice.lines), selectinload(Invoice.customer))
        )
        invoices = session.exec(statement).all()
    totals = {
        "standard": 0.0,
        "reduced": 0.0,
        "reverse": 0.0,
        "intracom": 0.0,
        "export": 0.0,
        "tax_standard": 0.0,
        "tax_reduced": 0.0,
    }
    for invoice in invoices:
        _, _, breakdown = compute_tax(invoice.lines)
        for entry in breakdown:
            if entry.category.value == "standard":
                totals["standard"] += entry.base
                totals["tax_standard"] += entry.tax
            elif entry.category.value == "reduced":
                totals["reduced"] += entry.base
                totals["tax_reduced"] += entry.tax
            elif entry.category.value == "reverse_charge":
                totals["reverse"] += entry.base
            elif entry.category.value == "eu_supply":
                totals["intracom"] += entry.base
            elif entry.category.value == "export":
                totals["export"] += entry.base
    return VATReturnSummary(
        taxable_turnover_standard=totals["standard"],
        taxable_turnover_reduced=totals["reduced"],
        reverse_charge_turnover=totals["reverse"],
        intra_community_supply=totals["intracom"],
        export_turnover=totals["export"],
        tax_amount_standard=totals["tax_standard"],
        tax_amount_reduced=totals["tax_reduced"],
    )


@router.post("/oss", response_model=list[OSSReport])
def oss_report(organization_id: int, payload: ReportRequest) -> list[OSSReport]:
    with get_session() as session:
        statement = (
            select(Invoice)
            .where(
                Invoice.organization_id == organization_id,
                Invoice.issue_date >= payload.start_date,
                Invoice.issue_date <= payload.end_date,
            )
            .options(selectinload(Invoice.lines), selectinload(Invoice.customer))
        )
        invoices = session.exec(statement).all()
    aggregated: dict[str, dict[str, float]] = defaultdict(lambda: {"net": 0.0, "tax": 0.0})
    for invoice in invoices:
        _, _, breakdown = compute_tax(invoice.lines)
        for entry in breakdown:
            key = f"{invoice.customer.country}:{entry.category.value}"
            aggregated[key]["net"] += entry.base
            aggregated[key]["tax"] += entry.tax
    reports: list[OSSReport] = []
    for key, values in aggregated.items():
        member_state, category = key.split(":")
        reports.append(
            OSSReport(
                member_state=member_state,
                supply_category=category,
                net_amount=values["net"],
                tax_amount=values["tax"],
            )
        )
    return reports
