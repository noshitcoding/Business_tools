from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def _install_pydantic_stub() -> None:
    if "pydantic" in sys.modules:
        return

    pydantic_stub = types.ModuleType("pydantic")

    class BaseSettings:
        def __init__(self, **values):
            for name, value in self.__class__.__dict__.items():
                if name.startswith("_") or callable(value):
                    continue
                setattr(self, name, value)
            for key, value in values.items():
                setattr(self, key, value)

    def Field(default=None, **kwargs):
        default_factory = kwargs.get("default_factory")
        if default_factory is not None:
            return default_factory()
        return default

    def validator(*args, **kwargs):  # type: ignore[override]
        def decorator(func):
            return func

        return decorator

    pydantic_stub.BaseSettings = BaseSettings
    pydantic_stub.Field = Field
    pydantic_stub.validator = validator
    sys.modules["pydantic"] = pydantic_stub


_install_pydantic_stub()


def _install_pendulum_stub() -> None:
    if "pendulum" in sys.modules:
        return

    pendulum_stub = types.ModuleType("pendulum")

    class _PendulumDateTime(datetime):
        def __new__(cls, *args, **kwargs):
            return datetime.__new__(cls, *args, **kwargs)

        def subtract(self, **kwargs):
            delta = timedelta(**kwargs)
            new_dt = datetime.__sub__(self, delta)
            return self.__class__.fromdatetime(new_dt)

        def format(self, fmt: str) -> str:
            replacements = {
                "YYYY": "%Y",
                "MM": "%m",
                "DD": "%d",
                "HH": "%H",
                "mm": "%M",
                "ss": "%S",
            }
            pattern = fmt
            for key, value in replacements.items():
                pattern = pattern.replace(key, value)
            return self.strftime(pattern)

        @classmethod
        def fromdatetime(cls, dt: datetime):
            return cls(
                dt.year,
                dt.month,
                dt.day,
                dt.hour,
                dt.minute,
                dt.second,
                dt.microsecond,
                dt.tzinfo,
            )

    def now(tz=None):
        tzinfo = tz
        if isinstance(tz, str):
            tzinfo = ZoneInfo(tz)
        base = datetime.now(tzinfo)
        return _PendulumDateTime.fromdatetime(base)

    pendulum_stub.now = now
    pendulum_stub.DateTime = _PendulumDateTime
    sys.modules["pendulum"] = pendulum_stub


_install_pendulum_stub()


def _install_sqlalchemy_stub() -> None:
    if "sqlalchemy" in sys.modules:
        return

    sqlalchemy_stub = types.ModuleType("sqlalchemy")

    def UniqueConstraint(*args, **kwargs):  # type: ignore[override]
        return (args, tuple(sorted(kwargs.items())))

    sqlalchemy_stub.UniqueConstraint = UniqueConstraint
    sys.modules["sqlalchemy"] = sqlalchemy_stub


def _install_sqlmodel_stub() -> None:
    if "sqlmodel" in sys.modules:
        return

    sqlmodel_stub = types.ModuleType("sqlmodel")

    class SQLModel:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    def Field(default=None, **kwargs):  # type: ignore[override]
        default_factory = kwargs.get("default_factory")
        if default_factory is not None:
            return default_factory()
        return default

    def Relationship(*args, **kwargs):  # type: ignore[override]
        return None

    sqlmodel_stub.SQLModel = SQLModel
    sqlmodel_stub.Field = Field
    sqlmodel_stub.Relationship = Relationship
    sys.modules["sqlmodel"] = sqlmodel_stub


_install_sqlalchemy_stub()
_install_sqlmodel_stub()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invoice_tool.config import get_settings
from invoice_tool.models import Invoice, InvoiceLine, InvoiceStatus, TaxCategory
from invoice_tool.services.tax import determine_status


def test_determine_status_marks_invoice_overdue_when_due_date_passed():
    settings = get_settings()
    timezone = ZoneInfo(settings.timezone)
    past_due_date = (datetime.now(timezone) - timedelta(days=1)).date()
    invoice = Invoice()
    invoice.organization_id = 1
    invoice.customer_id = 1
    invoice.invoice_number = "INV-001"
    invoice.status = InvoiceStatus.SENT
    invoice.due_date = past_due_date
    invoice.lines = []

    line = InvoiceLine()
    line.invoice_id = 1
    line.description = "Consulting"
    line.quantity = 1
    line.unit = "h"
    line.net_amount = 100.0
    line.tax_category = TaxCategory.STANDARD
    line.tax_rate = 0.19

    invoice.lines.append(line)

    determine_status(invoice, total_paid=10.0)

    assert invoice.status == InvoiceStatus.OVERDUE
