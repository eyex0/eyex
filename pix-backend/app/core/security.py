from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")
    # bcrypt max is 72 bytes
    pw_bytes = pw_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pw_bytes = plain.encode("utf-8")[:72]
        hash_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(subject: str) -> tuple[str, int]:
    expires_in = settings.access_token_expire_minutes * 60
    expire = datetime.now(UTC) + timedelta(seconds=expires_in)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    token = jwt.encode(payload, settings.app_secret_key, algorithm=settings.algorithm)
    return token, expires_in


def create_refresh_token(subject: str) -> tuple[str, int]:
    expires_in = settings.refresh_token_expire_days * 86400
    expire = datetime.now(UTC) + timedelta(seconds=expires_in)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.app_secret_key, algorithm=settings.algorithm)
    return token, expires_in


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.app_secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "expired"}
    except JWTError:
        return {"error": "invalid"}
