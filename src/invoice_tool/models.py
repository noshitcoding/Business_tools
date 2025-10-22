"""Database models for the invoice tool."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

import pendulum
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    updated_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))

    def touch(self) -> None:
        self.updated_at = pendulum.now("UTC")


class Country(str, Enum):
    DE = "DE"
    AT = "AT"
    CH = "CH"
    EU = "EU"


class TaxCategory(str, Enum):
    STANDARD = "standard"
    REDUCED = "reduced"
    ZERO = "zero"
    REVERSE_CHARGE = "reverse_charge"
    EU_SUPPLY = "eu_supply"
    EXPORT = "export"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    PARTLY_PAID = "partly_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class InvoiceType(str, Enum):
    REGULAR = "regular"
    CREDIT_NOTE = "credit_note"
    SELF_BILLING = "self_billing"
    ADVANCE = "advance"
    FINAL = "final"
    CORRECTION = "correction"


class Role(str, Enum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    APPROVER = "approver"
    USER = "user"


class Organization(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    legal_form: Optional[str] = None
    street: str
    postal_code: str
    city: str
    country: str = Field(default="DE")
    vat_id: Optional[str] = Field(default=None, description="USt-IdNr.")
    tax_number: Optional[str] = Field(default=None)
    email: Optional[str] = None
    phone: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    default_language: str = Field(default="de")
    default_currency: str = Field(default="EUR")

    invoices: list["Invoice"] = Relationship(back_populates="issuer")
    customers: list["Customer"] = Relationship(back_populates="organization")


class Customer(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    name: str
    street: str
    postal_code: str
    city: str
    country: str
    vat_id: Optional[str] = None
    email: Optional[str] = None
    language: str = Field(default="de")
    currency: str = Field(default="EUR")

    organization: Organization = Relationship(back_populates="customers")
    invoices: list["Invoice"] = Relationship(back_populates="customer")


class Article(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    number: str
    name: str
    description: Optional[str] = None
    unit: str = Field(default="h")
    net_price: float
    tax_category: TaxCategory = Field(default=TaxCategory.STANDARD)

    __table_args__ = (UniqueConstraint("organization_id", "number", name="article_number_unique"),)


class InvoiceLine(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    article_id: Optional[int] = Field(default=None, foreign_key="article.id")
    description: str
    quantity: float = Field(default=1)
    unit: str = Field(default="h")
    net_amount: float
    tax_category: TaxCategory = Field(default=TaxCategory.STANDARD)
    tax_rate: float = Field(default=0.19)

    invoice: "Invoice" = Relationship(back_populates="lines")


class Invoice(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    customer_id: int = Field(foreign_key="customer.id")
    invoice_number: str
    type: InvoiceType = Field(default=InvoiceType.REGULAR)
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT)
    issue_date: date = Field(default_factory=lambda: pendulum.now("Europe/Berlin").date())
    service_period_start: Optional[date] = None
    service_period_end: Optional[date] = None
    currency: str = Field(default="EUR")
    exchange_rate: Optional[float] = None
    reverse_charge: bool = False
    self_billing: bool = False
    tax_exemption_text: Optional[str] = None
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    base_document_number: Optional[str] = Field(
        default=None, description="Reference for correction or final invoices"
    )
    notes: Optional[str] = None

    issuer: Organization = Relationship(back_populates="invoices")
    customer: Customer = Relationship(back_populates="invoices")
    lines: list[InvoiceLine] = Relationship(back_populates="invoice")
    payments: list["Payment"] = Relationship(back_populates="invoice")
    reminders: list["Reminder"] = Relationship(back_populates="invoice")

    __table_args__ = (UniqueConstraint("organization_id", "invoice_number", name="invoice_number_unique"),)


class Payment(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    amount: float
    currency: str = Field(default="EUR")
    booking_date: date = Field(default_factory=lambda: pendulum.now("Europe/Berlin").date())
    reference: Optional[str] = None
    source: Optional[str] = Field(default="bank")

    invoice: Invoice = Relationship(back_populates="payments")


class Reminder(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    level: int = Field(default=1)
    sent_at: datetime = Field(default_factory=lambda: pendulum.now("UTC"))
    notes: Optional[str] = None

    invoice: Invoice = Relationship(back_populates="reminders")


class Approval(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    approver_id: int = Field(foreign_key="user.id")
    approved: bool = False
    comment: Optional[str] = None


class User(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    email: str = Field(index=True)
    full_name: str
    hashed_password: str
    role: Role = Field(default=Role.USER)
    otp_secret: Optional[str] = None
    is_active: bool = Field(default=True)

    approvals: list[Approval] = Relationship()


class AuditLog(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    entity: str
    entity_id: str
    action: str
    payload: str


class ArchiveEntry(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    filename: str
    storage_path: str
    sha256: str
    mime_type: str
    document_type: str = Field(default="invoice")
    valid_until: Optional[date] = None


class WebhookSubscription(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    target_url: str
    secret: str
    event_types: str


class IntegrationConfig(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    integration_type: str
    configuration: str
    active: bool = Field(default=True)


class RecurringInvoice(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    customer_id: int = Field(foreign_key="customer.id")
    template_name: str
    interval_days: int
    next_run: date
    last_invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    active: bool = Field(default=True)


class NumberSequence(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id")
    prefix: str
    last_number: int = Field(default=0)
    sequence_type: str = Field(default="invoice")

    __table_args__ = (UniqueConstraint("organization_id", "prefix", "sequence_type", name="number_sequence_unique"),)
