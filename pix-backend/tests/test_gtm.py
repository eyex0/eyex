from __future__ import annotations

import pytest

from app.api.v1.gtm import gtm_router
from app.models.gtm import IndustryVertical, LeadSource
from app.services.gtm_industry import INDUSTRY_PLAYBOOKS
from app.services.gtm_proof import ROICalculatorService, CaseStudyService
from app.services.gtm_sales import LeadScoringEngine, DemoWorkflowService


class TestGTMRouterImport:
    def test_router_exists(self):
        assert gtm_router is not None
        assert gtm_router.prefix == "/gtm"


class TestLeadScoringEngine:
    def test_scores_inbound_low(self):
        engine = LeadScoringEngine()
        lead = type("Lead", (), {
            "source": LeadSource.INBOUND,
            "industry": None,
            "employee_count": 10,
            "annual_revenue": 500_000,
        })
        score = engine.calculate_score(lead)
        assert 0 <= score <= 100

    def test_scores_demo_request_high(self):
        engine = LeadScoringEngine()
        lead = type("Lead", (), {
            "source": LeadSource.DEMO_REQUEST,
            "industry": IndustryVertical.FINANCE,
            "employee_count": 2000,
            "annual_revenue": 200_000_000,
        })
        score = engine.calculate_score(lead)
        assert score >= 80

    def test_industry_bonus(self):
        engine = LeadScoringEngine()
        lead = type("Lead", (), {
            "source": LeadSource.INBOUND,
            "industry": IndustryVertical.HEALTHCARE,
            "employee_count": 50,
            "annual_revenue": 5_000_000,
        })
        score = engine.calculate_score(lead)
        assert score > 50

    def test_capped_at_100(self):
        engine = LeadScoringEngine()
        lead = type("Lead", (), {
            "source": LeadSource.DEMO_REQUEST,
            "industry": IndustryVertical.FINANCE,
            "employee_count": 10000,
            "annual_revenue": 2_000_000_000,
        })
        score = engine.calculate_score(lead)
        assert score == 100


class TestDemoWorkflowService:
    def test_scenarios_exist(self):
        assert "standard" in DemoWorkflowService.SCENARIOS
        assert "executive" in DemoWorkflowService.SCENARIOS
        assert "technical" in DemoWorkflowService.SCENARIOS
        assert "industry" in DemoWorkflowService.SCENARIOS

    def test_get_scenario_config(self):
        service = DemoWorkflowService(None)
        config = service.get_scenario_config("standard")
        assert "name" in config
        assert "duration_minutes" in config
        assert "steps" in config

    def test_unknown_scenario_defaults(self):
        service = DemoWorkflowService(None)
        config = service.get_scenario_config("nonexistent")
        assert config["name"] == "Standard Enterprise Demo"


class TestIndustryPlaybooks:
    def test_all_five_industries(self):
        assert len(INDUSTRY_PLAYBOOKS) == 5
        assert IndustryVertical.MANUFACTURING in INDUSTRY_PLAYBOOKS
        assert IndustryVertical.HEALTHCARE in INDUSTRY_PLAYBOOKS
        assert IndustryVertical.LOGISTICS in INDUSTRY_PLAYBOOKS
        assert IndustryVertical.FINANCE in INDUSTRY_PLAYBOOKS
        assert IndustryVertical.RETAIL in INDUSTRY_PLAYBOOKS

    def test_manufacturing_playbook(self):
        playbook = INDUSTRY_PLAYBOOKS[IndustryVertical.MANUFACTURING]
        assert playbook.name == "Manufacturing Intelligence"
        assert len(playbook.key_problems) >= 4
        assert len(playbook.key_use_cases) >= 3
        assert len(playbook.roi_metrics) >= 2

    def test_finance_playbook_has_compliance(self):
        playbook = INDUSTRY_PLAYBOOKS[IndustryVertical.FINANCE]
        assert "SOX" in playbook.compliance_requirements
        assert "PCI-DSS" in playbook.compliance_requirements

    def test_pricing_guidance_present(self):
        for playbook in INDUSTRY_PLAYBOOKS.values():
            assert "starter_monthly" in playbook.pricing_guidance
            assert "enterprise_monthly" in playbook.pricing_guidance


class TestROICalculatorService:
    @pytest.mark.asyncio
    async def test_manufacturing_roi_positive(self):
        class FakeDB:
            async def flush(self): pass
            async def commit(self): pass
            async def refresh(self, obj): pass
            def add(self, obj): pass

        service = ROICalculatorService(FakeDB())
        calc = await service.calculate_manufacturing_roi(
            org_id="12345678-1234-5678-1234-567812345678",
            annual_revenue=50_000_000,
            downtime_cost_per_hour=10_000,
            annual_downtime_hours=500,
            maintenance_staff_count=20,
            avg_maintenance_salary=80_000,
            inventory_value=10_000_000,
            defect_rate=2.0,
        )
        assert calc.results["roi_percentage"] > 0
        assert calc.results["net_annual_value"] > 0

    @pytest.mark.asyncio
    async def test_finance_roi_positive(self):
        class FakeDB:
            async def flush(self): pass
            async def commit(self): pass
            async def refresh(self, obj): pass
            def add(self, obj): pass

        service = ROICalculatorService(FakeDB())
        calc = await service.calculate_finance_roi(
            org_id="12345678-1234-5678-1234-567812345678",
            annual_revenue=100_000_000,
            fraud_losses_last_year=2_000_000,
            compliance_staff_count=10,
            avg_compliance_salary=100_000,
            report_count_per_month=10,
            avg_hours_per_report=20,
            risk_review_count=50,
            avg_hours_per_review=8,
        )
        assert calc.results["roi_percentage"] > 0

    @pytest.mark.asyncio
    async def test_healthcare_roi_positive(self):
        class FakeDB:
            async def flush(self): pass
            async def commit(self): pass
            async def refresh(self, obj): pass
            def add(self, obj): pass

        service = ROICalculatorService(FakeDB())
        calc = await service.calculate_healthcare_roi(
            org_id="12345678-1234-5678-1234-567812345678",
            annual_operating_cost=500_000_000,
            overtime_annual_cost=8_000_000,
            patient_volume_annual=200_000,
            average_wait_time_minutes=40,
            denial_annual_loss=5_000_000,
            beds=500,
        )
        assert calc.results["roi_percentage"] > 0


class TestCaseStudyTemplates:
    def test_templates_exist(self):
        from app.services.gtm_proof import CASE_STUDY_TEMPLATES
        assert "novapay_finance" in CASE_STUDY_TEMPLATES
        assert "apex_manufacturing" in CASE_STUDY_TEMPLATES
        assert "metro_healthcare" in CASE_STUDY_TEMPLATES

    def test_template_has_metrics(self):
        from app.services.gtm_proof import CASE_STUDY_TEMPLATES
        template = CASE_STUDY_TEMPLATES["novapay_finance"]
        assert "revenue_protected" in template.metrics
        assert "cost_savings" in template.metrics

    def test_template_has_agents(self):
        from app.services.gtm_proof import CASE_STUDY_TEMPLATES
        template = CASE_STUDY_TEMPLATES["apex_manufacturing"]
        assert len(template.agents_used) > 0
        assert len(template.connectors_used) > 0
