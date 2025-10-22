"""Security related helpers and middleware for the invoice tool."""
from __future__ import annotations

from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add hardened security headers to every response."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        content_security_policy: str,
        referrer_policy: str,
        permissions_policy: str,
        strict_transport_security: str | None,
    ) -> None:
        super().__init__(app)
        self._content_security_policy = content_security_policy
        self._referrer_policy = referrer_policy
        self._permissions_policy = permissions_policy
        self._strict_transport_security = strict_transport_security

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response: Response = await call_next(request)
        response.headers.pop("server", None)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault("Referrer-Policy", self._referrer_policy)
        response.headers.setdefault("Permissions-Policy", self._permissions_policy)
        if self._content_security_policy:
            response.headers.setdefault("Content-Security-Policy", self._content_security_policy)
        if self._strict_transport_security and self._is_https_request(request):
            response.headers.setdefault("Strict-Transport-Security", self._strict_transport_security)
        return response

    @staticmethod
    def _is_https_request(request: Request) -> bool:
        if request.url.scheme.lower() == "https":
            return True
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto:
            proto = forwarded_proto.split(",", 1)[0].strip().lower()
            if proto == "https":
                return True
        return False
