from __future__ import annotations

import time

import pytest
from jose import jwt

from app.core import supabase_auth
from app.core.supabase_auth import decode_supabase_token, is_supabase_token


def _generate_es256_jwk_and_key():
    """Generate an EC P-256 keypair and return (private_key_pem, jwk_dict)."""
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()

    def _b64(n: int) -> str:
        from jose.utils import base64url_encode

        return base64url_encode(n.to_bytes(32, "big")).decode("utf-8")

    jwk_dict = {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64(public_numbers.x),
        "y": _b64(public_numbers.y),
        "kid": "test-kid-1",
        "alg": "ES256",
        "use": "sig",
    }
    return private_key, jwk_dict


@pytest.fixture(autouse=True)
def _clear_jwks_cache():
    supabase_auth._jwks_cache["keys"] = None
    supabase_auth._jwks_cache["fetched_at"] = 0.0
    yield
    supabase_auth._jwks_cache["keys"] = None
    supabase_auth._jwks_cache["fetched_at"] = 0.0


class TestIsSupabaseToken:
    def test_detects_auth_v1_issuer(self):
        token = jwt.encode(
            {"iss": "https://project.supabase.co/auth/v1", "sub": "abc"},
            "secret",
            algorithm="HS256",
        )
        assert is_supabase_token(token) is True

    def test_detects_authenticated_role(self):
        token = jwt.encode({"role": "authenticated", "sub": "abc"}, "secret", algorithm="HS256")
        assert is_supabase_token(token) is True

    def test_rejects_unrelated_token(self):
        token = jwt.encode({"sub": "abc", "type": "access"}, "secret", algorithm="HS256")
        assert is_supabase_token(token) is False


class TestDecodeSupabaseTokenLegacySecret(object):
    def test_hs256_shared_secret_success(self, monkeypatch):
        settings = supabase_auth.get_settings()
        monkeypatch.setattr(settings, "supabase_jwks_url", "", raising=False)
        monkeypatch.setattr(settings, "supabase_jwt_secret", "my-secret", raising=False)
        supabase_auth.get_settings.cache_clear()
        monkeypatch.setattr(supabase_auth, "get_settings", lambda: settings)

        token = jwt.encode({"sub": "user-1", "email": "a@b.com"}, "my-secret", algorithm="HS256")
        payload = decode_supabase_token(token)
        assert payload.get("sub") == "user-1"
        assert "error" not in payload

    def test_missing_config_returns_error(self, monkeypatch):
        settings = supabase_auth.get_settings()
        monkeypatch.setattr(settings, "supabase_jwks_url", "", raising=False)
        monkeypatch.setattr(settings, "supabase_jwt_secret", "", raising=False)
        monkeypatch.setattr(supabase_auth, "get_settings", lambda: settings)

        token = jwt.encode({"sub": "user-1"}, "whatever", algorithm="HS256")
        payload = decode_supabase_token(token)
        assert payload.get("error") == "missing_config"


class TestDecodeSupabaseTokenJWKS:
    def test_es256_jwks_verification_success(self, monkeypatch):
        private_key, jwk_dict = _generate_es256_jwk_and_key()

        pem = private_key.private_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.PEM,
            format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PrivateFormat"]).PrivateFormat.PKCS8,
            encryption_algorithm=__import__("cryptography.hazmat.primitives.serialization", fromlist=["NoEncryption"]).NoEncryption(),
        )

        token = jwt.encode(
            {"sub": "user-42", "email": "demo@pix.app", "role": "authenticated", "exp": int(time.time()) + 3600},
            pem,
            algorithm="ES256",
            headers={"kid": "test-kid-1"},
        )

        settings = supabase_auth.get_settings()
        monkeypatch.setattr(settings, "supabase_jwks_url", "https://fake.supabase.co/jwks.json", raising=False)
        monkeypatch.setattr(settings, "supabase_jwt_secret", "", raising=False)
        monkeypatch.setattr(supabase_auth, "get_settings", lambda: settings)
        monkeypatch.setattr(supabase_auth, "_fetch_jwks", lambda url: [jwk_dict])

        payload = decode_supabase_token(token)
        assert "error" not in payload, payload
        assert payload["sub"] == "user-42"
        assert payload["email"] == "demo@pix.app"

    def test_es256_jwks_verification_wrong_key_fails(self, monkeypatch):
        private_key, _ = _generate_es256_jwk_and_key()
        _, other_jwk = _generate_es256_jwk_and_key()

        pem = private_key.private_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.PEM,
            format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PrivateFormat"]).PrivateFormat.PKCS8,
            encryption_algorithm=__import__("cryptography.hazmat.primitives.serialization", fromlist=["NoEncryption"]).NoEncryption(),
        )
        token = jwt.encode(
            {"sub": "user-42", "exp": int(time.time()) + 3600},
            pem,
            algorithm="ES256",
            headers={"kid": "test-kid-1"},
        )

        settings = supabase_auth.get_settings()
        monkeypatch.setattr(settings, "supabase_jwks_url", "https://fake.supabase.co/jwks.json", raising=False)
        monkeypatch.setattr(settings, "supabase_jwt_secret", "", raising=False)
        monkeypatch.setattr(supabase_auth, "get_settings", lambda: settings)
        # Serve a JWKS containing only a different key with the same kid -> signature mismatch.
        other_jwk["kid"] = "test-kid-1"
        monkeypatch.setattr(supabase_auth, "_fetch_jwks", lambda url: [other_jwk])

        payload = decode_supabase_token(token)
        assert payload.get("error") == "invalid"
