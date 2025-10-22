"""Security helpers for authentication, 2FA and audit."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

import pyotp
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from ..config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_token_cache: Optional[Fernet] = None


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd_context.verify(password, hashed)


def _get_signer() -> Fernet:
    global _token_cache
    if _token_cache is None:
        settings = get_settings()
        key_path = settings.secrets_path / "signing.key"
        if not key_path.exists():
            key_path.write_bytes(Fernet.generate_key())
        _token_cache = Fernet(key_path.read_bytes())
    return _token_cache


def generate_access_token(user_id: int, expires_in: int = 3600) -> str:
    payload = {
        "sub": user_id,
        "exp": (datetime.utcnow() + timedelta(seconds=expires_in)).timestamp(),
        "iat": datetime.utcnow().timestamp(),
    }
    data = json.dumps(payload).encode("utf-8")
    return _get_signer().encrypt(data).decode("utf-8")


def decode_access_token(token: str) -> dict:
    data = _get_signer().decrypt(token.encode("utf-8"))
    payload = json.loads(data)
    if payload.get("exp") and payload["exp"] < datetime.utcnow().timestamp():
        raise ValueError("Token expired")
    return payload


def generate_otp_secret() -> str:
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    settings = get_settings()
    return pyotp.TOTP(secret, issuer=settings.two_factor_issuer)


def verify_otp(secret: str, code: str) -> bool:
    totp = get_totp(secret)
    return totp.verify(code, valid_window=1)
