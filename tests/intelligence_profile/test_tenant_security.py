"""Tests for ProfileTenantGuard."""
import pytest
from packages.cognitive_kernel.intelligence_profile.tenant_security import ProfileTenantGuard, TENANT_TABLES


class TestTenantSecurity:
    def test_validate_org_id_valid(self):
        result = ProfileTenantGuard.validate_org_id("org_123")
        assert result == "org_123"

    def test_validate_org_id_none(self):
        with pytest.raises(ValueError, match="organization_id is required"):
            ProfileTenantGuard.validate_org_id(None)

    def test_validate_org_id_empty(self):
        with pytest.raises(ValueError, match="organization_id is required"):
            ProfileTenantGuard.validate_org_id("")

    def test_tenant_tables_list(self):
        assert "intelligence_profiles" in TENANT_TABLES
        assert "profile_ontology" in TENANT_TABLES
        assert "profile_kpis" in TENANT_TABLES
        assert "profile_glossary" in TENANT_TABLES
        assert "profile_data_sources" in TENANT_TABLES
        assert "profile_events" in TENANT_TABLES
        assert "profile_semantic_history" in TENANT_TABLES
        assert "profile_versions" in TENANT_TABLES
