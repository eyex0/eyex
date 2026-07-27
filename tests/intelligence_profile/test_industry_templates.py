"""Tests for IndustryTemplateRegistry."""
from packages.cognitive_kernel.intelligence_profile.industry_templates import IndustryTemplateRegistry


class TestIndustryTemplates:
    def setup_method(self):
        self.registry = IndustryTemplateRegistry()

    def test_list_templates(self):
        templates = self.registry.list_templates()
        assert len(templates) == 7
        assert "retail" in templates
        assert "manufacturing" in templates
        assert "finance" in templates
        assert "healthcare" in templates
        assert "logistics" in templates
        assert "saas" in templates
        assert "construction" in templates

    def test_get_template_retail(self):
        template = self.registry.get_template("retail")
        assert template is not None
        assert template.industry == "retail"
        assert len(template.entities) >= 4
        assert len(template.kpis) >= 3
        assert len(template.departments) >= 3
        assert len(template.recommended_agents) >= 2
        assert len(template.terminology) >= 2

    def test_get_template_dict(self):
        template_dict = self.registry.get_template_dict("manufacturing")
        assert template_dict is not None
        assert "entities" in template_dict
        assert "kpis" in template_dict
        assert "departments" in template_dict

    def test_get_unknown_template(self):
        assert self.registry.get_template("nonexistent") is None

    def test_list_all_templates(self):
        all_templates = self.registry.list_all_templates()
        assert len(all_templates) == 7
        for t in all_templates:
            assert "industry" in t
            assert "description" in t
            assert "entity_count" in t
            assert "kpi_count" in t

    def test_each_template_has_required_fields(self):
        for industry in self.registry.list_templates():
            template = self.registry.get_template(industry)
            assert template is not None
            assert len(template.entities) > 0
            assert len(template.kpis) > 0
            assert len(template.departments) > 0
            assert len(template.recommended_agents) > 0
            for entity in template.entities:
                assert "entity_type" in entity
                assert "aliases" in entity
                assert "properties_schema" in entity
            for kpi in template.kpis:
                assert "name" in kpi
                assert "formula" in kpi
                assert "target" in kpi
