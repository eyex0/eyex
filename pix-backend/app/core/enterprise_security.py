from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("pix.core.enterprise_security")

try:
    from cryptography.fernet import Fernet

    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False


def _get_fernet(secret_key: str | None = None) -> Any:
    if not _CRYPTO_AVAILABLE:
        return None
    key = secret_key or os.environ.get("APP_SECRET_KEY")
    if not key:
        raise RuntimeError(
            "APP_SECRET_KEY environment variable is required for encryption operations."
        )
    if len(key) < 32:
        logger.warning("APP_SECRET_KEY is shorter than 32 bytes; padding to 32 bytes")
    key_bytes = key.encode() if isinstance(key, str) else key
    if len(key_bytes) > 32:
        key_bytes = key_bytes[:32]
    elif len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"x")
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(value: str, secret_key: str | None = None) -> str:
    fernet = _get_fernet(secret_key)
    if fernet is None:
        logger.warning("Encryption unavailable (cryptography not installed)")
        return value
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str, secret_key: str | None = None) -> str:
    fernet = _get_fernet(secret_key)
    if fernet is None:
        return encrypted
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except Exception as exc:
        logger.error("Decryption failed: %s", exc)
        return encrypted


def hash_sensitive(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def sign_payload(payload: dict, secret_key: str) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        secret_key.encode(), data.encode(), hashlib.sha256
    ).hexdigest()


def verify_signature(payload: dict, signature: str, secret_key: str) -> bool:
    expected = sign_payload(payload, secret_key)
    return hmac.compare_digest(expected, signature)


@dataclass
class AuditLogEntry:
    action: str
    actor_id: str
    resource_type: str
    resource_id: str
    org_id: str
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    timestamp: str = ""


class AuditLogger:
    """Immutable audit log for enterprise compliance.

    Logs all security-relevant actions with tamper-evident chaining.
    """

    def __init__(self) -> None:
        self._entries: list[AuditLogEntry] = []
        self._chain: list[str] = []

    def log(
        self,
        action: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        org_id: str = "default",
        details: dict[str, Any] | None = None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            org_id=org_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._entries.append(entry)

        chain_input = f"{entry.timestamp}|{entry.action}|{entry.actor_id}|{entry.resource_id}"
        if self._chain:
            chain_input += f"|{self._chain[-1]}"
        chain_hash = hashlib.sha256(chain_input.encode()).hexdigest()
        self._chain.append(chain_hash)

        logger.info(
            "AUDIT: %s on %s[%s] by %s (org=%s)",
            action, resource_type, resource_id, actor_id, org_id,
        )
        return entry

    def get_entries(
        self, org_id: str | None = None, action: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[dict[str, Any]]:
        entries = self._entries
        if org_id:
            entries = [e for e in entries if e.org_id == org_id]
        if action:
            entries = [e for e in entries if e.action == action]
        entries = entries[offset:offset + limit]
        return [
            {
                "action": e.action, "actor_id": e.actor_id,
                "resource_type": e.resource_type, "resource_id": e.resource_id,
                "org_id": e.org_id, "details": e.details,
                "ip_address": e.ip_address, "timestamp": e.timestamp,
            }
            for e in entries
        ]

    def verify_chain(self) -> bool:
        if not self._chain:
            return True
        for i in range(len(self._entries)):
            entry = self._entries[i]
            chain_input = f"{entry.timestamp}|{entry.action}|{entry.actor_id}|{entry.resource_id}"
            if i > 0:
                chain_input += f"|{self._chain[i-1]}"
            expected_hash = hashlib.sha256(chain_input.encode()).hexdigest()
            if self._chain[i] != expected_hash:
                return False
        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "chain_integrity": self.verify_chain(),
            "unique_actions": len(set(e.action for e in self._entries)),
            "unique_actors": len(set(e.actor_id for e in self._entries)),
        }


_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
