from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.config import settings
from app.db import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class TokenData:
    user_id: str
    email: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user: User) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": now,
        "exp": now + settings.jwt_expiration_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return TokenData(user_id=user_id, email=email)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth_header.replace("Bearer ", "").strip()
    token_data = decode_token(token)
    user = db.execute(select(User).where(User.id == token_data.user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.replace("Bearer ", "").strip()
    try:
        token_data = decode_token(token)
    except HTTPException:
        return None
    user = db.execute(select(User).where(User.id == token_data.user_id)).scalar_one_or_none()
    return user


def require_token(token: str | None) -> TokenData:
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    return decode_token(token)


def oauth_exchange_code(token_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    import httpx

    response = httpx.post(token_url, data=payload, timeout=20.0)
    response.raise_for_status()
    return response.json()


def oauth_fetch_profile(profile_url: str, access_token: str) -> dict[str, Any]:
    import httpx

    headers = {"Authorization": f"Bearer {access_token}"}
    response = httpx.get(profile_url, headers=headers, timeout=20.0)
    response.raise_for_status()
    return response.json()
