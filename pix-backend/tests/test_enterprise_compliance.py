from __future__ import annotations

import os

import pytest

from app.core.enterprise_compliance import (
    ComplianceFramework,
    DataEncryptionService,
    EnterpriseSecurityManager,
    Permission,
    RBACProvider,
    SSOProvider,
    get_security_manager,
)


class TestPermission:
    def test_permission_values(self):
        assert Permission.ORG_READ.value == "org:read"
        assert Permission.AGENT_EXECUTE.value == "agent:execute"
        assert Permission.ADMIN_SYSTEM.value == "admin:system"


class TestRBACProvider:
    def test_superadmin_has_all_permissions(self):
        rbac = RBACProvider()
        assert rbac.has_permission("superadmin", Permission.ADMIN_SYSTEM)
        assert rbac.has_permission("superadmin", Permission.ORG_DELETE)
        assert rbac.has_permission("superadmin", Permission.BILLING_WRITE)

    def test_admin_has_org_permissions(self):
        rbac = RBACProvider()
        assert rbac.has_permission("admin", Permission.ORG_READ)
        assert rbac.has_permission("admin", Permission.ORG_WRITE)
        assert rbac.has_permission("admin", Permission.ORG_MANAGE)
        assert not rbac.has_permission("admin", Permission.ORG_DELETE)
        assert not rbac.has_permission("admin", Permission.ADMIN_SYSTEM)

    def test_member_limited_permissions(self):
        rbac = RBACProvider()
        assert rbac.has_permission("member", Permission.WORKSPACE_READ)
        assert rbac.has_permission("member", Permission.AGENT_EXECUTE)
        assert not rbac.has_permission("member", Permission.MEMBER_MANAGE)
        assert not rbac.has_permission("member", Permission.BILLING_WRITE)

    def test_viewer_read_only(self):
        rbac = RBACProvider()
        assert rbac.has_permission("viewer", Permission.WORKSPACE_READ)
        assert rbac.has_permission("viewer", Permission.AGENT_READ)
        assert not rbac.has_permission("viewer", Permission.AGENT_EXECUTE)
        assert not rbac.has_permission("viewer", Permission.MEMBER_READ)

    def test_has_any_permission(self):
        rbac = RBACProvider()
        assert rbac.has_any_permission("admin", [Permission.ORG_READ, Permission.ORG_DELETE])
        assert not rbac.has_any_permission("viewer", [Permission.AGENT_EXECUTE, Permission.MEMBER_READ])

    def test_has_all_permissions(self):
        rbac = RBACProvider()
        assert rbac.has_all_permissions("admin", [Permission.ORG_READ, Permission.ORG_WRITE])
        assert not rbac.has_all_permissions("member", [Permission.WORKSPACE_READ, Permission.MEMBER_MANAGE])

    def test_get_role_permissions(self):
        rbac = RBACProvider()
        perms = rbac.get_role_permissions("viewer")
        assert Permission.WORKSPACE_READ in perms
        assert Permission.AGENT_READ in perms
        assert Permission.AGENT_EXECUTE not in perms

    def test_unknown_role_returns_empty(self):
        rbac = RBACProvider()
        assert rbac.get_role_permissions("nonexistent") == set()
        assert not rbac.has_permission("nonexistent", Permission.ORG_READ)

    def test_custom_role_creation(self):
        rbac = RBACProvider()
        rbac.create_custom_role("custom_admin", [Permission.ORG_READ, Permission.WORKSPACE_READ])
        assert rbac.has_permission("custom_admin", Permission.ORG_READ)
        assert rbac.has_permission("custom_admin", Permission.WORKSPACE_READ)
        assert not rbac.has_permission("custom_admin", Permission.ORG_WRITE)
        assert rbac.validate_role("custom_admin")

    def test_validate_role(self):
        rbac = RBACProvider()
        assert rbac.validate_role("admin")
        assert rbac.validate_role("superadmin")
        assert not rbac.validate_role("hacker")

    def test_get_all_roles(self):
        rbac = RBACProvider()
        roles = rbac.get_all_roles()
        assert "superadmin" in roles["built_in"]
        assert "admin" in roles["built_in"]
        assert "member" in roles["built_in"]
        assert "viewer" in roles["built_in"]

    def test_custom_role_persists_permissions(self):
        rbac = RBACProvider()
        rbac.create_custom_role("auditor", [Permission.AUDIT_READ, Permission.AUDIT_EXPORT])
        perms = rbac.get_role_permissions("auditor")
        assert Permission.AUDIT_READ in perms
        assert Permission.AUDIT_EXPORT in perms
        assert Permission.ORG_READ not in perms


class TestSSOProvider:
    def test_configure_oidc(self):
        sso = SSOProvider()
        sso.configure("oidc", {
            "issuer_url": "https://accounts.google.com",
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "redirect_uri": "https://app.pix.ai/auth/callback",
            "scopes": ["openid", "profile", "email"],
        })
        assert sso.is_configured("oidc")

    def test_configure_saml(self):
        sso = SSOProvider()
        sso.configure("saml", {
            "issuer_url": "https://idp.example.com",
            "client_id": "saml-client",
            "client_secret": "saml-secret",
            "redirect_uri": "https://app.pix.ai/auth/saml/callback",
            "idp_certificate": "MIID...",
            "sso_url": "https://idp.example.com/sso",
        })
        assert sso.is_configured("saml")

    def test_unsupported_provider(self):
        sso = SSOProvider()
        with pytest.raises(ValueError, match="Unsupported SSO provider"):
            sso.configure("unsupported", {})

    def test_missing_required_fields(self):
        sso = SSOProvider()
        with pytest.raises(ValueError, match="Missing required config"):
            sso.configure("oidc", {"issuer_url": "https://example.com"})

    def test_get_providers(self):
        sso = SSOProvider()
        sso.configure("oidc", {
            "issuer_url": "https://accounts.google.com",
            "client_id": "test",
            "client_secret": "test",
            "redirect_uri": "https://app.pix.ai/callback",
            "scopes": ["openid"],
        })
        providers = sso.get_providers()
        assert len(providers) == 1
        assert providers[0]["provider"] == "oidc"

    def test_not_configured(self):
        sso = SSOProvider()
        assert not sso.is_configured("oidc")


class TestComplianceFramework:
    def test_get_frameworks(self):
        cf = ComplianceFramework()
        frameworks = cf.get_frameworks()
        assert len(frameworks) == 3
        names = {f["key"] for f in frameworks}
        assert names == {"soc2", "gdpr", "hipaa"}

    def test_get_status(self):
        cf = ComplianceFramework()
        status = cf.get_status("gdpr")
        assert len(status) == 8
        assert all(s["status"] == "pending" for s in status)

    def test_mark_implemented(self):
        cf = ComplianceFramework()
        assert cf.mark_implemented("soc2", "CC6.1", evidence="Encryption at rest enabled")
        status = cf.get_status("soc2")
        cc61 = next(s for s in status if s["control_id"] == "CC6.1")
        assert cc61["status"] == "implemented"
        assert "Encryption at rest enabled" in cc61["evidence"]

    def test_mark_nonexistent_control(self):
        cf = ComplianceFramework()
        assert not cf.mark_implemented("soc2", "NONEXISTENT")

    def test_mark_nonexistent_framework(self):
        cf = ComplianceFramework()
        assert not cf.mark_implemented("nonexistent", "CC1.1")

    def test_get_overall_status(self):
        cf = ComplianceFramework()
        status = cf.get_overall_status()
        assert status["total_controls"] == 21
        assert status["implemented"] == 0
        assert status["compliance_pct"] == 0.0

    def test_get_overall_status_partial(self):
        cf = ComplianceFramework()
        cf.mark_implemented("soc2", "CC6.1")
        cf.mark_implemented("gdpr", "Art 5")
        status = cf.get_overall_status()
        assert status["implemented"] == 2
        assert status["compliance_pct"] == pytest.approx(9.5, rel=0.1)


class TestDataEncryptionService:
    def test_encrypt_decrypt_roundtrip(self):
        service = DataEncryptionService(master_key="test-master-key-32-bytes-long!!")
        original = "sensitive-data-123"
        encrypted = service.encrypt_field(original, context="test")
        assert encrypted != original
        decrypted = service.decrypt_field(encrypted, context="test")
        assert decrypted == original

    def test_encrypt_empty_string(self):
        service = DataEncryptionService(master_key="test-key")
        assert service.encrypt_field("", "test") == ""
        assert service.decrypt_field("", "test") == ""

    def test_different_contexts_different_keys(self):
        service = DataEncryptionService(master_key="test-key")
        v1 = service.encrypt_field("secret", context="db")
        v2 = service.encrypt_field("secret", context="cache")
        assert v1 != v2

    def test_key_rotation(self):
        service = DataEncryptionService(master_key="test-key")
        v1 = service.encrypt_field("secret", context="test")
        rotation = service.rotate_key()
        assert rotation["previous_version"] == 0
        assert rotation["new_version"] == 1
        v2 = service.encrypt_field("secret", context="test")
        assert v1 != v2
        decrypted = service.decrypt_field(v2, context="test")
        assert decrypted == "secret"

    def test_get_stats(self):
        service = DataEncryptionService(master_key="test-key")
        service.encrypt_field("secret1", context="a")
        service.encrypt_field("secret2", context="b")
        stats = service.get_stats()
        assert stats["key_version"] == 0
        assert stats["cached_contexts"] == 2
        assert stats["total_rotations"] == 0
        assert stats["last_rotation"] is None

    def test_multiple_rotations(self):
        service = DataEncryptionService(master_key="test-key")
        service.rotate_key()
        service.rotate_key()
        stats = service.get_stats()
        assert stats["total_rotations"] == 2
        assert stats["key_version"] == 2


class TestEnterpriseSecurityManager:
    def test_singleton(self):
        m1 = get_security_manager()
        m2 = get_security_manager()
        assert m1 is m2

    def test_mfa_toggle(self):
        mgr = EnterpriseSecurityManager()
        assert not mgr.is_mfa_enabled()
        mgr.enable_mfa()
        assert mgr.is_mfa_enabled()
        mgr.disable_mfa()
        assert not mgr.is_mfa_enabled()

    def test_get_security_status(self):
        mgr = EnterpriseSecurityManager()
        status = mgr.get_security_status()
        assert "rbac_roles" in status
        assert "sso_providers" in status
        assert "compliance" in status
        assert "encryption" in status
        assert "mfa_enabled" in status

    def test_all_components_accessible(self):
        mgr = EnterpriseSecurityManager()
        assert mgr.rbac is not None
        assert mgr.sso is not None
        assert mgr.compliance is not None
        assert mgr.encryption is not None
        assert mgr.rbac.has_permission("superadmin", Permission.ADMIN_SYSTEM)
