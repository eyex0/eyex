from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("pix.core.compliance")


class Permission(Enum):
    ORG_READ = "org:read"
    ORG_WRITE = "org:write"
    ORG_DELETE = "org:delete"
    ORG_MANAGE = "org:manage"
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_MANAGE = "workspace:manage"
    MEMBER_READ = "member:read"
    MEMBER_INVITE = "member:invite"
    MEMBER_REMOVE = "member:remove"
    MEMBER_MANAGE = "member:manage"
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_EXECUTE = "agent:execute"
    AGENT_DEPLOY = "agent:deploy"
    API_KEY_READ = "api_key:read"
    API_KEY_CREATE = "api_key:create"
    API_KEY_REVOKE = "api_key:revoke"
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    ADMIN_PANEL = "admin:panel"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"
    INTEGRATION_READ = "integration:read"
    INTEGRATION_WRITE = "integration:write"
    INTEGRATION_DELETE = "integration:delete"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "superadmin": set(Permission),
    "admin": {
        Permission.ORG_READ, Permission.ORG_WRITE, Permission.ORG_MANAGE,
        Permission.WORKSPACE_READ, Permission.WORKSPACE_WRITE, Permission.WORKSPACE_DELETE, Permission.WORKSPACE_MANAGE,
        Permission.MEMBER_READ, Permission.MEMBER_INVITE, Permission.MEMBER_REMOVE, Permission.MEMBER_MANAGE,
        Permission.AGENT_READ, Permission.AGENT_WRITE, Permission.AGENT_EXECUTE, Permission.AGENT_DEPLOY,
        Permission.API_KEY_READ, Permission.API_KEY_CREATE, Permission.API_KEY_REVOKE,
        Permission.BILLING_READ, Permission.BILLING_WRITE,
        Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
        Permission.INTEGRATION_READ, Permission.INTEGRATION_WRITE, Permission.INTEGRATION_DELETE,
    },
    "owner": {
        Permission.ORG_READ, Permission.ORG_WRITE, Permission.ORG_MANAGE,
        Permission.WORKSPACE_READ, Permission.WORKSPACE_WRITE, Permission.WORKSPACE_DELETE, Permission.WORKSPACE_MANAGE,
        Permission.MEMBER_READ, Permission.MEMBER_INVITE, Permission.MEMBER_REMOVE, Permission.MEMBER_MANAGE,
        Permission.AGENT_READ, Permission.AGENT_WRITE, Permission.AGENT_EXECUTE, Permission.AGENT_DEPLOY,
        Permission.API_KEY_READ, Permission.API_KEY_CREATE, Permission.API_KEY_REVOKE,
        Permission.BILLING_READ, Permission.BILLING_WRITE,
        Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
        Permission.INTEGRATION_READ, Permission.INTEGRATION_WRITE, Permission.INTEGRATION_DELETE,
    },
    "member": {
        Permission.WORKSPACE_READ,
        Permission.AGENT_READ, Permission.AGENT_EXECUTE,
        Permission.API_KEY_READ, Permission.API_KEY_CREATE,
    },
    "viewer": {
        Permission.WORKSPACE_READ,
        Permission.AGENT_READ,
    },
}


class RBACProvider:
    def __init__(self) -> None:
        self._role_permissions = {role: perms.copy() for role, perms in ROLE_PERMISSIONS.items()}
        self._custom_roles: dict[str, set[Permission]] = {}

    def has_permission(self, role: str, permission: Permission) -> bool:
        if role in self._custom_roles:
            return permission in self._custom_roles[role]
        return permission in self._role_permissions.get(role, set())

    def has_any_permission(self, role: str, permissions: list[Permission]) -> bool:
        return any(self.has_permission(role, p) for p in permissions)

    def has_all_permissions(self, role: str, permissions: list[Permission]) -> bool:
        return all(self.has_permission(role, p) for p in permissions)

    def get_role_permissions(self, role: str) -> set[Permission]:
        if role in self._custom_roles:
            return self._custom_roles[role].copy()
        return self._role_permissions.get(role, set()).copy()

    def create_custom_role(self, name: str, permissions: list[Permission]) -> None:
        self._custom_roles[name] = set(permissions)

    def validate_role(self, role: str) -> bool:
        return role in self._role_permissions or role in self._custom_roles

    def get_all_roles(self) -> dict[str, list[str]]:
        return {
            "built_in": list(self._role_permissions.keys()),
            "custom": list(self._custom_roles.keys()),
        }


class SSOProvider:
    def __init__(self) -> None:
        self._providers: dict[str, dict[str, Any]] = {}

    def configure(self, provider: str, config: dict[str, Any]) -> None:
        supported = {"saml", "oidc", "google_workspace", "azure_ad", "okta"}
        if provider not in supported:
            raise ValueError(f"Unsupported SSO provider '{provider}'. Supported: {supported}")
        required = self._get_required_fields(provider)
        missing = [f for f in required if f not in config]
        if missing:
            raise ValueError(f"Missing required config for {provider}: {missing}")
        self._providers[provider] = {**config, "configured_at": datetime.now(UTC).isoformat()}
        logger.info("SSO provider '%s' configured", provider)

    def _get_required_fields(self, provider: str) -> list[str]:
        base = {"issuer_url", "client_id", "client_secret", "redirect_uri"}
        if provider == "saml":
            return list(base | {"idp_certificate", "sso_url"})
        if provider == "oidc":
            return list(base | {"scopes"})
        if provider in ("google_workspace", "azure_ad", "okta"):
            return list(base | {"tenant_id", "scopes"})
        return list(base)

    def is_configured(self, provider: str) -> bool:
        return provider in self._providers

    def get_providers(self) -> list[dict[str, Any]]:
        return [
            {"provider": name, "configured_at": config["configured_at"]}
            for name, config in self._providers.items()
        ]


@dataclass
class ComplianceRequirement:
    framework: str
    control_id: str
    description: str
    status: str = "pending"
    implemented_at: str = ""
    evidence: list[str] = field(default_factory=list)


class ComplianceFramework:
    FRAMEWORKS = {
        "soc2": {
            "name": "SOC 2",
            "controls": [
                "CC1.1 - Control Environment",
                "CC2.1 - Communication and Information",
                "CC3.1 - Risk Assessment",
                "CC4.1 - Monitoring Activities",
                "CC5.1 - Control Activities",
                "CC6.1 - Logical and Physical Access",
                "CC7.1 - System Operations",
                "CC8.1 - Change Management",
            ],
        },
        "gdpr": {
            "name": "GDPR",
            "controls": [
                "Art 5 - Lawful Processing",
                "Art 15 - Data Access",
                "Art 17 - Right to Erasure",
                "Art 20 - Data Portability",
                "Art 25 - Data Protection by Design",
                "Art 32 - Security of Processing",
                "Art 33 - Breach Notification",
                "Art 35 - Data Protection Impact Assessment",
            ],
        },
        "hipaa": {
            "name": "HIPAA",
            "controls": [
                "164.308 - Administrative Safeguards",
                "164.310 - Physical Safeguards",
                "164.312 - Technical Safeguards",
                "164.314 - Organizational Requirements",
                "164.316 - Policies and Procedures",
            ],
        },
    }

    def __init__(self) -> None:
        self._requirements: dict[str, list[ComplianceRequirement]] = {}
        for fw, info in self.FRAMEWORKS.items():
            self._requirements[fw] = [
                ComplianceRequirement(framework=fw, control_id=c.split(" - ")[0], description=c.split(" - ")[1])
                for c in info["controls"]
            ]

    def get_frameworks(self) -> list[dict[str, Any]]:
        return [
            {"key": k, "name": v["name"], "controls": v["controls"]}
            for k, v in self.FRAMEWORKS.items()
        ]

    def get_status(self, framework: str) -> list[dict[str, Any]]:
        reqs = self._requirements.get(framework, [])
        return [
            {"control_id": r.control_id, "description": r.description, "status": r.status, "implemented_at": r.implemented_at, "evidence": r.evidence}
            for r in reqs
        ]

    def mark_implemented(self, framework: str, control_id: str, evidence: str | None = None) -> bool:
        for req in self._requirements.get(framework, []):
            if req.control_id == control_id:
                req.status = "implemented"
                req.implemented_at = datetime.now(UTC).isoformat()
                if evidence:
                    req.evidence.append(evidence)
                return True
        return False

    def get_overall_status(self) -> dict[str, Any]:
        total = 0
        implemented = 0
        for fw in self._requirements:
            for req in self._requirements[fw]:
                total += 1
                if req.status == "implemented":
                    implemented += 1
        return {
            "total_controls": total,
            "implemented": implemented,
            "compliance_pct": round(implemented / max(total, 1) * 100, 1),
            "frameworks": {
                fw: {
                    "total": len(reqs),
                    "implemented": sum(1 for r in reqs if r.status == "implemented"),
                }
                for fw, reqs in self._requirements.items()
            },
        }


class DataEncryptionService:
    def __init__(self, master_key: str | None = None) -> None:
        self._master_key = master_key or os.environ.get("APP_SECRET_KEY", "")
        self._key_cache: dict[str, tuple[str, datetime]] = {}
        self._rotation_history: list[dict[str, Any]] = []

    def encrypt_field(self, value: str, context: str = "default") -> str:
        if not value:
            return value
        from app.core.enterprise_security import encrypt_value
        return encrypt_value(value, secret_key=self._derive_key(context))

    def decrypt_field(self, encrypted: str, context: str = "default") -> str:
        if not encrypted:
            return encrypted
        from app.core.enterprise_security import decrypt_value
        return decrypt_value(encrypted, secret_key=self._derive_key(context))

    def _derive_key(self, context: str) -> str:
        if context in self._key_cache:
            key, expires_at = self._key_cache[context]
            if datetime.now(UTC) < expires_at:
                return key
        material = f"{self._master_key}:{context}:{self._get_key_version()}"
        derived = hashlib.sha256(material.encode()).hexdigest()
        self._key_cache[context] = (derived, datetime.now(UTC) + timedelta(hours=1))
        return derived

    def _get_key_version(self) -> int:
        return len(self._rotation_history)

    def rotate_key(self) -> dict[str, Any]:
        rotation = {
            "timestamp": datetime.now(UTC).isoformat(),
            "previous_version": self._get_key_version(),
            "new_version": self._get_key_version() + 1,
        }
        self._rotation_history.append(rotation)
        self._key_cache.clear()
        logger.info("Encryption key rotated to version %d", rotation["new_version"])
        return rotation

    def get_stats(self) -> dict[str, Any]:
        return {
            "key_version": self._get_key_version(),
            "cached_contexts": len(self._key_cache),
            "total_rotations": len(self._rotation_history),
            "last_rotation": self._rotation_history[-1] if self._rotation_history else None,
        }


class EnterpriseSecurityManager:
    def __init__(self) -> None:
        self.rbac = RBACProvider()
        self.sso = SSOProvider()
        self.compliance = ComplianceFramework()
        self.encryption = DataEncryptionService()
        self._mfa_enabled = False

    def enable_mfa(self) -> None:
        self._mfa_enabled = True

    def disable_mfa(self) -> None:
        self._mfa_enabled = False

    def is_mfa_enabled(self) -> bool:
        return self._mfa_enabled

    def get_security_status(self) -> dict[str, Any]:
        return {
            "rbac_roles": self.rbac.get_all_roles(),
            "sso_providers": self.sso.get_providers(),
            "compliance": self.compliance.get_overall_status(),
            "encryption": self.encryption.get_stats(),
            "mfa_enabled": self._mfa_enabled,
        }


_security_manager: EnterpriseSecurityManager | None = None


def get_security_manager() -> EnterpriseSecurityManager:
    global _security_manager
    if _security_manager is None:
        _security_manager = EnterpriseSecurityManager()
    return _security_manager
