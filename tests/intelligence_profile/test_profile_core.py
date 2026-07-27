"""Tests for IntelligenceProfile dataclass."""
from packages.cognitive_kernel.intelligence_profile.profile_core import IntelligenceProfile


class TestIntelligenceProfile:
    def test_to_dict(self):
        profile = IntelligenceProfile(
            id="test-id",
            organization_id="org-123",
            industry="retail",
            business_model="b2c",
            company_size="mid",
            region="EU",
            locations=[{"country": "Italy"}],
            profile_config={"departments": ["Sales"]},
            confidence_score=0.75,
            status="active",
            current_version=3,
        )
        d = profile.to_dict()
        assert d["id"] == "test-id"
        assert d["organization_id"] == "org-123"
        assert d["industry"] == "retail"
        assert d["confidence_score"] == 0.75
        assert d["status"] == "active"
        assert d["current_version"] == 3
        assert d["profile_config"]["departments"] == ["Sales"]

    def test_defaults(self):
        profile = IntelligenceProfile(id="x", organization_id="org")
        assert profile.industry is None
        assert profile.business_model is None
        assert profile.locations == []
        assert profile.profile_config == {}
        assert profile.confidence_score == 0.0
        assert profile.status == "draft"
        assert profile.current_version == 1
