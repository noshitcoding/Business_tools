"""Pydantic schemas used by the API."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, validator

from .models import InvoiceStatus, InvoiceType, Role, TaxCategory


class Address(BaseModel):
    name: str
    street: str
    postal_code: str
    city: str
    country: str = Field(regex=r"^[A-Z]{2}$")
    vat_id: Optional[str] = Field(default=None, regex=r"^[A-Z]{2}[A-Z0-9]{2,12}$")


class PaymentTerms(BaseModel):
    description: str
    due_days: int = Field(ge=0, le=120)
    discount_percent: Optional[float] = Field(default=None, ge=0, le=100)
    discount_days: Optional[int] = Field(default=None, ge=0, le=60)


class InvoiceLineIn(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit: str = "h"
    net_amount: float = Field(ge=0)
    tax_category: TaxCategory = TaxCategory.STANDARD
    tax_rate: float = Field(ge=0, le=1)


class InvoiceCreate(BaseModel):
    organization_id: int
    customer_id: int
    lines: list[InvoiceLineIn]
    invoice_number: Optional[str] = None
    type: InvoiceType = InvoiceType.REGULAR
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: Optional[date] = None
    service_period_start: Optional[date] = None
    service_period_end: Optional[date] = None
    currency: str = "EUR"
    exchange_rate: Optional[float] = Field(default=None, gt=0)
    reverse_charge: bool = False
    self_billing: bool = False
    tax_exemption_text: Optional[str] = None
    payment_terms: Optional[PaymentTerms] = None
    due_date: Optional[date] = None
    base_document_number: Optional[str] = None
    notes: Optional[str] = None

    @validator("due_date", always=True)
    def compute_due_date(cls, value: Optional[date], values: dict) -> Optional[date]:
        if value is not None:
            return value
        issue_date: Optional[date] = values.get("issue_date")
        terms: Optional[PaymentTerms] = values.get("payment_terms")
        if issue_date and terms:
            return issue_date + timedelta(days=terms.due_days)
        return value


class InvoiceRead(BaseModel):
    id: int
    invoice_number: str
    status: InvoiceStatus
    type: InvoiceType
    issue_date: date
    due_date: Optional[date]
    total_net: float
    total_tax: float
    total_gross: float
    currency: str
    reverse_charge: bool
    self_billing: bool
    created_at: datetime


class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float
    currency: str = "EUR"
    booking_date: Optional[date] = None
    reference: Optional[str] = None
    source: Literal["bank", "psp", "manual"] = "bank"


class PaymentRead(BaseModel):
    id: int
    invoice_id: int
    amount: float
    currency: str
    booking_date: date
    created_at: datetime


class UserCreate(BaseModel):
    organization_id: int
    email: str
    full_name: str
    password: str
    role: Role = Role.USER


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    otp_enabled: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str
    otp: Optional[str] = None


class TwoFactorSetup(BaseModel):
    secret: str
    uri: str


class VATValidationResponse(BaseModel):
    vat_id: str
    valid: bool
    trader_name: Optional[str]
    trader_address: Optional[str]
    consultation_number: Optional[str]
    checked_at: datetime


class ArchiveDocument(BaseModel):
    id: int
    filename: str
    sha256: str
    mime_type: str
    stored_at: datetime
    document_type: str


class EPCQRCodeRequest(BaseModel):
    name: str = Field(description="Empfängername, max. 70 Zeichen")
    iban: str
    bic: Optional[str]
    amount: float
    remittance_information: str = Field(max_length=140)
    purpose: Optional[str] = Field(default=None, max_length=4)
    version: Literal["001", "002"] = "002"


class EPCQRCodeResponse(BaseModel):
    payload: str
    svg: str
    png_base64: str


class ReportRequest(BaseModel):
    start_date: date
    end_date: date

    @validator("end_date")
    def validate_dates(cls, value: date, values: dict) -> date:
        if value < values["start_date"]:
            raise ValueError("end_date must be after start_date")
        return value


class VATReturnSummary(BaseModel):
    taxable_turnover_standard: float
    taxable_turnover_reduced: float
    reverse_charge_turnover: float
    intra_community_supply: float
    export_turnover: float
    tax_amount_standard: float
    tax_amount_reduced: float


class OSSReport(BaseModel):
    member_state: str
    supply_category: str
    net_amount: float
    tax_amount: float


class RecurringInvoiceCreate(BaseModel):
    organization_id: int
    customer_id: int
    template_name: str
    interval_days: int
    next_run: date
    active: bool = True


class WebhookSubscriptionCreate(BaseModel):
    organization_id: int
    target_url: HttpUrl
    event_types: list[str]


class WebhookSubscriptionRead(BaseModel):
    id: int
    target_url: HttpUrl
    event_types: list[str]
    secret: str
