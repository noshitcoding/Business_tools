"""User management endpoints with 2FA support."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..db import get_session
from ..models import User
from ..schemas import AuthResponse, LoginRequest, TwoFactorSetup, UserCreate, UserRead
from ..services.security import (
    generate_access_token,
    generate_otp_secret,
    get_totp,
    hash_password,
    verify_otp,
    verify_password,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead)
def create_user(payload: UserCreate) -> UserRead:
    with get_session() as session:
        existing = session.exec(select(User).where(User.email == payload.email)).one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(
            organization_id=payload.organization_id,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=payload.role,
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        return UserRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            otp_enabled=bool(user.otp_secret),
        )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    with get_session() as session:
        user = session.exec(select(User).where(User.email == payload.email)).one_or_none()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if user.otp_secret:
            if not payload.otp or not verify_otp(user.otp_secret, payload.otp):
                raise HTTPException(status_code=401, detail="Invalid OTP")
        token = generate_access_token(user.id)
        return AuthResponse(access_token=token)


@router.post("/{user_id}/2fa", response_model=TwoFactorSetup)
def enable_two_factor(user_id: int) -> TwoFactorSetup:
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        secret = generate_otp_secret()
        user.otp_secret = secret
        session.add(user)
        session.flush()
        totp = get_totp(secret)
        return TwoFactorSetup(secret=secret, uri=totp.provisioning_uri(user.email))


@router.get("", response_model=list[UserRead])
def list_users(organization_id: int) -> list[UserRead]:
    with get_session() as session:
        users = session.exec(select(User).where(User.organization_id == organization_id)).all()
        return [
            UserRead(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                otp_enabled=bool(user.otp_secret),
            )
            for user in users
        ]
