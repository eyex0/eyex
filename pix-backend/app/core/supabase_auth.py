from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.config import get_settings

logger = logging.getLogger("pix.core.supabase_auth")

_JWKS_CACHE_TTL_SECONDS = 3600
_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}


def _fetch_jwks(jwks_url: str) -> list[dict[str, Any]]:
    """Fetch and cache the JWKS key set from Supabase, refreshing on TTL expiry."""
    now = time.monotonic()
    if _jwks_cache["keys"] is not None and (now - _jwks_cache["fetched_at"]) < _JWKS_CACHE_TTL_SECONDS:
        return _jwks_cache["keys"]

    try:
        response = httpx.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        keys = response.json().get("keys", [])
        _jwks_cache["keys"] = keys
        _jwks_cache["fetched_at"] = now
        return keys
    except Exception as exc:
        logger.warning("Failed to fetch Supabase JWKS from %s: %s", jwks_url, exc)
        if _jwks_cache["keys"] is not None:
            return _jwks_cache["keys"]
        return []


def _find_jwk(keys: list[dict[str, Any]], kid: str | None) -> dict[str, Any] | None:
    if not keys:
        return None
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
    # Fall back to the first key if no kid match (single-key JWKS).
    return keys[0] if len(keys) == 1 else None


def _decode_with_jwks(token: str, jwks_url: str) -> dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        return {"error": "invalid"}

    kid = unverified_header.get("kid")
    alg = unverified_header.get("alg", "ES256")

    keys = _fetch_jwks(jwks_url)
    matching_key = _find_jwk(keys, kid)
    if not matching_key:
        # Retry once with a forced cache refresh in case of key rotation.
        _jwks_cache["keys"] = None
        keys = _fetch_jwks(jwks_url)
        matching_key = _find_jwk(keys, kid)
    if not matching_key:
        return {"error": "invalid"}

    try:
        public_key = jwk.construct(matching_key, alg)
        message, encoded_sig = token.rsplit(".", 1)
        decoded_sig = base64url_decode(encoded_sig.encode("utf-8"))
        if not public_key.verify(message.encode("utf-8"), decoded_sig):
            return {"error": "invalid"}
        payload = jwt.decode(
            token,
            matching_key,
            algorithms=[alg],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "expired"}
    except JWTError as exc:
        logger.debug("Supabase JWKS token decode failed: %s", exc)
        return {"error": "invalid"}
    except Exception as exc:
        logger.debug("Supabase JWKS token verification failed: %s", exc)
        return {"error": "invalid"}


def _decode_with_secret(token: str, secret: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "expired"}
    except JWTError as exc:
        logger.debug("Supabase token decode failed: %s", exc)
        return {"error": "invalid"}


def decode_supabase_token(token: str) -> dict[str, Any]:
    """Decode and validate a Supabase JWT.

    Prefers JWKS-based verification (ES256/RS256, the default for modern
    Supabase projects). Falls back to the legacy HS256 shared-secret method
    when SUPABASE_JWT_SECRET is configured instead of/in addition to JWKS.
    Returns a dict with user metadata on success, or {"error": "..."} on failure.
    """
    settings = get_settings()

    if settings.supabase_jwks_url:
        result = _decode_with_jwks(token, settings.supabase_jwks_url)
        if "error" not in result:
            return result
        # If JWKS verification failed but a legacy secret is also configured, try it.
        if settings.supabase_jwt_secret:
            return _decode_with_secret(token, settings.supabase_jwt_secret)
        return result

    if settings.supabase_jwt_secret:
        return _decode_with_secret(token, settings.supabase_jwt_secret)

    return {"error": "missing_config"}


def is_supabase_token(token: str) -> bool:
    """Heuristic to detect a Supabase-issued JWT.

    Supabase tokens (HS256 legacy or ES256/RS256 current) contain a
    recognizable issuer or role claim.
    """
    try:
        unverified = jwt.get_unverified_claims(token)
        iss = str(unverified.get("iss", ""))
        return bool(
            iss == "supabase"
            or "/auth/v1" in iss
            or unverified.get("role") == "anon"
            or unverified.get("role") == "authenticated"
        )
    except Exception:
        return False


def extract_user_id(payload: dict[str, Any]) -> str | None:
    """Extract the user identifier from a Supabase JWT payload."""
    return payload.get("sub")


def extract_user_email(payload: dict[str, Any]) -> str | None:
    """Extract the user email from a Supabase JWT payload."""
    return payload.get("email")
