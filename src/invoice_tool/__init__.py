"""Invoice Tool package implementing a German-compliant invoicing platform."""

from importlib.metadata import version

__all__ = ["get_version"]


def get_version() -> str:
    """Return the installed package version."""
    try:
        return version("invoice-tool")
    except Exception:  # pragma: no cover - fallback if package metadata missing
        return "0.1.0"
