"""
πX Industry Templates — Pre-built starting points for common industries.

Templates are NOT forced schemas. They provide a starting ontology, KPI set,
department structure, and recommended agents that the company can accept, modify,
or reject entirely. The profile is always adaptive.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("pix.intelligence_profile.templates")


class IndustryTemplate:
    """A single industry template with default ontology, KPIs, departments, and agents."""

    def __init__(
        self,
        industry: str,
        description: str,
        entities: list[dict],
        kpis: list[dict],
        departments: list[dict],
        recommended_agents: list[dict],
        terminology: list[dict],
    ):
        self.industry = industry
        self.description = description
        self.entities = entities
        self.kpis = kpis
        self.departments = departments
        self.recommended_agents = recommended_agents
        self.terminology = terminology

    def to_dict(self) -> dict:
        return {
            "industry": self.industry,
            "description": self.description,
            "entities": self.entities,
            "kpis": self.kpis,
            "departments": self.departments,
            "recommended_agents": self.recommended_agents,
            "terminology": self.terminology,
        }


# ── Template Definitions ──────────────────────────────────────────────

MANUFACTURING = IndustryTemplate(
    industry="manufacturing",
    description="Discrete and process manufacturing operations",
    entities=[
        {"entity_type": "product", "label": "Product", "aliases": ["item", "sku", "part", "component"],
         "properties_schema": {"fields": [{"name": "sku", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "cost", "type": "currency"}]}},
        {"entity_type": "work_order", "label": "Work Order", "aliases": ["production order", "mo", "manufacturing order"],
         "properties_schema": {"fields": [{"name": "order_id", "type": "identifier"}, {"name": "product", "type": "reference"}, {"name": "quantity", "type": "quantity"}, {"name": "status", "type": "category"}]}},
        {"entity_type": "equipment", "label": "Equipment", "aliases": ["machine", "asset", "line", "station"],
         "properties_schema": {"fields": [{"name": "equipment_id", "type": "identifier"}, {"name": "type", "type": "category"}, {"name": "status", "type": "category"}]}},
        {"entity_type": "supplier", "label": "Supplier", "aliases": ["vendor", "provider"],
         "properties_schema": {"fields": [{"name": "supplier_id", "type": "identifier"}, {"name": "name", "type": "text"}]}},
        {"entity_type": "material", "label": "Material", "aliases": ["raw material", "bom component", "ingredient"],
         "properties_schema": {"fields": [{"name": "material_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "unit_cost", "type": "currency"}]}},
    ],
    kpis=[
        {"name": "oee", "label": "Overall Equipment Effectiveness", "category": "operations",
         "definition": "Availability × Performance × Quality",
         "formula": {"type": "calculated", "expression": "availability * performance * quality"},
         "target": {"value": 0.85, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["overall_equipment_effectiveness"]},
        {"name": "cycle_time", "label": "Cycle Time", "category": "operations",
         "definition": "Time to produce one unit",
         "formula": {"type": "avg", "field": "production_time"},
         "target": {"value": 60, "unit": "minutes", "direction": "lower_better"},
         "aliases": ["production_time", "takt_time"]},
        {"name": "first_pass_yield", "label": "First Pass Yield", "category": "quality",
         "definition": "Percentage of units that pass quality check on first attempt",
         "formula": {"type": "ratio", "numerator": "good_units", "denominator": "total_units"},
         "target": {"value": 0.95, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["fpY", "first_pass_quality"]},
        {"name": "inventory_turnover", "label": "Inventory Turnover", "category": "operations",
         "definition": "How often inventory is sold and replaced",
         "formula": {"type": "ratio", "numerator": "cogs", "denominator": "avg_inventory"},
         "target": {"value": 8, "unit": "turns/year", "direction": "higher_better"},
         "aliases": ["stock_turnover"]},
    ],
    departments=[
        {"name": "Production", "roles": ["Plant Manager", "Production Supervisor", "Operator"]},
        {"name": "Quality", "roles": ["Quality Manager", "Inspector", "QA Engineer"]},
        {"name": "Supply Chain", "roles": ["Supply Chain Manager", "Buyer", "Logistics Coordinator"]},
        {"name": "Engineering", "roles": ["Process Engineer", "Maintenance Engineer"]},
    ],
    recommended_agents=[
        {"name": "Production Intelligence Agent", "role": "Monitor OEE, cycle times, and production bottlenecks"},
        {"name": "Quality Intelligence Agent", "role": "Track yield, defect rates, and quality trends"},
        {"name": "Supply Chain Agent", "role": "Monitor supplier performance, material availability, and inventory"},
    ],
    terminology=[
        {"term": "OEE", "definition": "Overall Equipment Effectiveness", "aliases": ["oee", "equipment_effectiveness"]},
        {"term": "BOM", "definition": "Bill of Materials", "aliases": ["bom", "bill_of_materials", "material_list"]},
        {"term": "MO", "definition": "Manufacturing Order", "aliases": ["mo", "work_order", "production_order"]},
    ],
)

RETAIL = IndustryTemplate(
    industry="retail",
    description="Retail operations, stores, and merchandising",
    entities=[
        {"entity_type": "store", "label": "Store", "aliases": ["shop", "location", "outlet", "branch"],
         "properties_schema": {"fields": [{"name": "store_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "region", "type": "category"}]}},
        {"entity_type": "product", "label": "Product", "aliases": ["item", "sku", "merchandise"],
         "properties_schema": {"fields": [{"name": "sku", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "category", "type": "category"}, {"name": "price", "type": "currency"}]}},
        {"entity_type": "customer", "label": "Customer", "aliases": ["cust", "client", "buyer", "shopper"],
         "properties_schema": {"fields": [{"name": "customer_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "loyalty_tier", "type": "category"}]}},
        {"entity_type": "promotion", "label": "Promotion", "aliases": ["promo", "campaign", "discount", "offer"],
         "properties_schema": {"fields": [{"name": "promo_id", "type": "identifier"}, {"name": "type", "type": "category"}, {"name": "discount", "type": "percentage"}]}},
        {"entity_type": "transaction", "label": "Transaction", "aliases": ["sale", "purchase", "receipt"],
         "properties_schema": {"fields": [{"name": "transaction_id", "type": "identifier"}, {"name": "amount", "type": "currency"}, {"name": "date", "type": "date"}]}},
    ],
    kpis=[
        {"name": "revenue", "label": "Revenue", "category": "revenue",
         "definition": "Total sales revenue",
         "formula": {"type": "sum", "field": "net_rev"},
         "target": {"value": 1000000, "unit": "EUR", "period": "monthly", "direction": "higher_better"},
         "aliases": ["net_rev", "sales", "net_revenue", "turnover"]},
        {"name": "margin", "label": "Gross Margin", "category": "revenue",
         "definition": "Revenue minus cost of goods sold",
         "formula": {"type": "calculated", "expression": "revenue - cogs"},
         "target": {"value": 0.4, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["gross_margin", "gm"]},
        {"name": "sell_out", "label": "Sell-out Rate", "category": "operations",
         "definition": "Percentage of inventory sold to end customer",
         "formula": {"type": "ratio", "numerator": "units_sold", "denominator": "units_available"},
         "target": {"value": 0.8, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["sell_out_rate", "sellout"]},
        {"name": "inventory_turn", "label": "Inventory Turnover", "category": "operations",
         "definition": "How often inventory is sold and replaced",
         "formula": {"type": "ratio", "numerator": "cogs", "denominator": "avg_inventory"},
         "target": {"value": 12, "unit": "turns/year", "direction": "higher_better"},
         "aliases": ["stock_turn", "inventory_turnover"]},
    ],
    departments=[
        {"name": "Store Operations", "roles": ["Store Manager", "Assistant Manager", "Sales Associate"]},
        {"name": "Merchandising", "roles": ["Merchandising Manager", "Buyer", "Category Manager"]},
        {"name": "Marketing", "roles": ["Marketing Manager", "Campaign Manager"]},
        {"name": "Supply Chain", "roles": ["Logistics Manager", "Warehouse Supervisor"]},
    ],
    recommended_agents=[
        {"name": "Sales Intelligence Agent", "role": "Monitor revenue, margins, and sell-out across stores"},
        {"name": "Inventory Agent", "role": "Track stock levels, turnover, and reorder points"},
        {"name": "Customer Insights Agent", "role": "Analyze customer behavior, loyalty, and segmentation"},
    ],
    terminology=[
        {"term": "Sell-out", "definition": "Sales to end customer", "aliases": ["sell_out", "sellout", "end_customer_sales"]},
        {"term": "Sell-in", "definition": "Sales from brand to retailer", "aliases": ["sell_in", "sellin", "wholesale_sales"]},
        {"term": "SKU", "definition": "Stock Keeping Unit", "aliases": ["sku", "item_code", "product_code"]},
    ],
)

FINANCE = IndustryTemplate(
    industry="finance",
    description="Banking, investment, and financial services",
    entities=[
        {"entity_type": "account", "label": "Account", "aliases": ["bank_account", "portfolio", "wallet"],
         "properties_schema": {"fields": [{"name": "account_id", "type": "identifier"}, {"name": "type", "type": "category"}, {"name": "balance", "type": "currency"}]}},
        {"entity_type": "transaction", "label": "Transaction", "aliases": ["txn", "transfer", "payment", "trx"],
         "properties_schema": {"fields": [{"name": "transaction_id", "type": "identifier"}, {"name": "amount", "type": "currency"}, {"name": "type", "type": "category"}]}},
        {"entity_type": "client", "label": "Client", "aliases": ["customer", "investor", "borrower", "account_holder"],
         "properties_schema": {"fields": [{"name": "client_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "risk_score", "type": "numeric"}]}},
        {"entity_type": "instrument", "label": "Financial Instrument", "aliases": ["security", "bond", "stock", "fund"],
         "properties_schema": {"fields": [{"name": "isin", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "price", "type": "currency"}]}},
    ],
    kpis=[
        {"name": "aum", "label": "Assets Under Management", "category": "revenue",
         "definition": "Total market value of assets managed",
         "formula": {"type": "sum", "field": "portfolio_value"},
         "target": {"value": 500000000, "unit": "EUR", "direction": "higher_better"},
         "aliases": ["assets_under_management", "aum"]},
        {"name": "npl_ratio", "label": "Non-Performing Loan Ratio", "category": "risk",
         "definition": "Percentage of loans in default",
         "formula": {"type": "ratio", "numerator": "npl_amount", "denominator": "total_loans"},
         "target": {"value": 0.03, "unit": "ratio", "direction": "lower_better"},
         "aliases": ["npl", "default_rate"]},
        {"name": "cost_to_income", "label": "Cost-to-Income Ratio", "category": "operations",
         "definition": "Operating costs as percentage of income",
         "formula": {"type": "ratio", "numerator": "operating_costs", "denominator": "operating_income"},
         "target": {"value": 0.55, "unit": "ratio", "direction": "lower_better"},
         "aliases": ["cir", "cost_income_ratio"]},
    ],
    departments=[
        {"name": "Retail Banking", "roles": ["Branch Manager", "Relationship Manager", "Teller"]},
        {"name": "Risk Management", "roles": ["Risk Manager", "Credit Analyst", "Risk Modeler"]},
        {"name": "Investment", "roles": ["Portfolio Manager", "Investment Analyst", "Trader"]},
        {"name": "Compliance", "roles": ["Compliance Officer", "AML Specialist"]},
    ],
    recommended_agents=[
        {"name": "Risk Intelligence Agent", "role": "Monitor NPL ratios, credit risk, and exposure"},
        {"name": "Portfolio Intelligence Agent", "role": "Track AUM, performance, and allocation"},
        {"name": "Compliance Agent", "role": "Monitor regulatory requirements and AML alerts"},
    ],
    terminology=[
        {"term": "AUM", "definition": "Assets Under Management", "aliases": ["aum", "assets_under_management"]},
        {"term": "NPL", "definition": "Non-Performing Loan", "aliases": ["npl", "non_performing", "defaulted_loan"]},
        {"term": "ISIN", "definition": "International Securities Identification Number", "aliases": ["isin", "security_id"]},
    ],
)

HEALTHCARE = IndustryTemplate(
    industry="healthcare",
    description="Hospitals, clinics, and healthcare operations",
    entities=[
        {"entity_type": "patient", "label": "Patient", "aliases": ["patient", "beneficiary", "member"],
         "properties_schema": {"fields": [{"name": "patient_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "age", "type": "numeric"}]}},
        {"entity_type": "procedure", "label": "Medical Procedure", "aliases": ["treatment", "intervention", "service"],
         "properties_schema": {"fields": [{"name": "procedure_code", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "cost", "type": "currency"}]}},
        {"entity_type": "provider", "label": "Healthcare Provider", "aliases": ["doctor", "physician", "practitioner", "clinician"],
         "properties_schema": {"fields": [{"name": "provider_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "specialty", "type": "category"}]}},
        {"entity_type": "department", "label": "Clinical Department", "aliases": ["ward", "unit", "clinic"],
         "properties_schema": {"fields": [{"name": "department_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "type", "type": "category"}]}},
    ],
    kpis=[
        {"name": "bed_occupancy", "label": "Bed Occupancy Rate", "category": "operations",
         "definition": "Percentage of occupied beds",
         "formula": {"type": "ratio", "numerator": "occupied_beds", "denominator": "total_beds"},
         "target": {"value": 0.85, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["occupancy_rate", "bed_occupancy"]},
        {"name": "avg_los", "label": "Average Length of Stay", "category": "operations",
         "definition": "Average days a patient stays",
         "formula": {"type": "avg", "field": "length_of_stay"},
         "target": {"value": 4, "unit": "days", "direction": "lower_better"},
         "aliases": ["los", "avg_length_of_stay"]},
        {"name": "patient_satisfaction", "label": "Patient Satisfaction Score", "category": "quality",
         "definition": "Average patient satisfaction rating",
         "formula": {"type": "avg", "field": "satisfaction_score"},
         "target": {"value": 4.5, "unit": "score", "direction": "higher_better"},
         "aliases": ["satisfaction", "nps"]},
    ],
    departments=[
        {"name": "Emergency", "roles": ["ER Director", "ER Physician", "Triage Nurse"]},
        {"name": "Surgery", "roles": ["Surgeon", "Surgical Nurse", "Anesthesiologist"]},
        {"name": "Inpatient", "roles": ["Attending Physician", "Staff Nurse", "Charge Nurse"]},
        {"name": "Outpatient", "roles": ["Clinic Physician", "Medical Assistant"]},
    ],
    recommended_agents=[
        {"name": "Patient Flow Agent", "role": "Monitor bed occupancy, length of stay, and admissions"},
        {"name": "Quality of Care Agent", "role": "Track patient outcomes, satisfaction, and readmission rates"},
        {"name": "Resource Planning Agent", "role": "Optimize staffing, scheduling, and capacity"},
    ],
    terminology=[
        {"term": "LOS", "definition": "Length of Stay", "aliases": ["los", "length_of_stay", "stay_duration"]},
        {"term": "ICD", "definition": "International Classification of Diseases", "aliases": ["icd", "diagnosis_code"]},
        {"term": "CPT", "definition": "Current Procedural Terminology", "aliases": ["cpt", "procedure_code"]},
    ],
)

LOGISTICS = IndustryTemplate(
    industry="logistics",
    description="Freight, shipping, and supply chain logistics",
    entities=[
        {"entity_type": "shipment", "label": "Shipment", "aliases": ["cargo", "consignment", "load", "order"],
         "properties_schema": {"fields": [{"name": "shipment_id", "type": "identifier"}, {"name": "origin", "type": "text"}, {"name": "destination", "type": "text"}, {"name": "status", "type": "category"}]}},
        {"entity_type": "vehicle", "label": "Vehicle", "aliases": ["truck", "trailer", "fleet_unit", "asset"],
         "properties_schema": {"fields": [{"name": "vehicle_id", "type": "identifier"}, {"name": "type", "type": "category"}, {"name": "capacity", "type": "numeric"}]}},
        {"entity_type": "route", "label": "Route", "aliases": ["lane", "corridor", "path"],
         "properties_schema": {"fields": [{"name": "route_id", "type": "identifier"}, {"name": "origin", "type": "text"}, {"name": "destination", "type": "text"}, {"name": "distance", "type": "numeric"}]}},
        {"entity_type": "warehouse", "label": "Warehouse", "aliases": ["depot", "hub", "facility", "dc"],
         "properties_schema": {"fields": [{"name": "warehouse_id", "type": "identifier"}, {"name": "location", "type": "text"}, {"name": "capacity", "type": "numeric"}]}},
    ],
    kpis=[
        {"name": "on_time_delivery", "label": "On-Time Delivery Rate", "category": "operations",
         "definition": "Percentage of shipments delivered on time",
         "formula": {"type": "ratio", "numerator": "on_time_shipments", "denominator": "total_shipments"},
         "target": {"value": 0.95, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["otd", "on_time", "delivery_rate"]},
        {"name": "cost_per_shipment", "label": "Cost per Shipment", "category": "cost",
         "definition": "Average cost per shipment",
         "formula": {"type": "avg", "field": "shipment_cost"},
         "target": {"value": 50, "unit": "EUR", "direction": "lower_better"},
         "aliases": ["avg_shipment_cost", "cost_per_delivery"]},
        {"name": "fleet_utilization", "label": "Fleet Utilization", "category": "operations",
         "definition": "Percentage of fleet capacity utilized",
         "formula": {"type": "ratio", "numerator": "active_vehicles", "denominator": "total_vehicles"},
         "target": {"value": 0.85, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["vehicle_utilization", "fleet_usage"]},
    ],
    departments=[
        {"name": "Operations", "roles": ["Operations Manager", "Dispatcher", "Coordinator"]},
        {"name": "Fleet Management", "roles": ["Fleet Manager", "Driver", "Mechanic"]},
        {"name": "Warehouse", "roles": ["Warehouse Manager", "Forklift Operator", "Inventory Clerk"]},
        {"name": "Customer Service", "roles": ["CS Manager", "Tracking Specialist"]},
    ],
    recommended_agents=[
        {"name": "Route Optimization Agent", "role": "Optimize routes, reduce transit times, and minimize costs"},
        {"name": "Fleet Intelligence Agent", "role": "Monitor vehicle utilization, maintenance, and fuel consumption"},
        {"name": "Delivery Tracking Agent", "role": "Track shipments, predict delays, and alert on exceptions"},
    ],
    terminology=[
        {"term": "OTD", "definition": "On-Time Delivery", "aliases": ["otd", "on_time_delivery"]},
        {"term": "DC", "definition": "Distribution Center", "aliases": ["dc", "distribution_center", "depot"]},
        {"term": "TEU", "definition": "Twenty-foot Equivalent Unit", "aliases": ["teu", "container_unit"]},
    ],
)

SAAS = IndustryTemplate(
    industry="saas",
    description="Software-as-a-Service company operations",
    entities=[
        {"entity_type": "subscription", "label": "Subscription", "aliases": ["plan", "license", "seat", "account"],
         "properties_schema": {"fields": [{"name": "subscription_id", "type": "identifier"}, {"name": "plan", "type": "category"}, {"name": "mrr", "type": "currency"}]}},
        {"entity_type": "user", "label": "User", "aliases": ["end_user", "seat", "member", "account"],
         "properties_schema": {"fields": [{"name": "user_id", "type": "identifier"}, {"name": "email", "type": "email"}, {"name": "status", "type": "category"}]}},
        {"entity_type": "feature", "label": "Feature", "aliases": ["module", "capability", "function"],
         "properties_schema": {"fields": [{"name": "feature_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "status", "type": "category"}]}},
        {"entity_type": "tenant", "label": "Tenant", "aliases": ["workspace", "organization", "company", "customer"],
         "properties_schema": {"fields": [{"name": "tenant_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "plan", "type": "category"}]}},
    ],
    kpis=[
        {"name": "mrr", "label": "Monthly Recurring Revenue", "category": "revenue",
         "definition": "Total predictable monthly revenue",
         "formula": {"type": "sum", "field": "monthly_revenue"},
         "target": {"value": 100000, "unit": "EUR", "period": "monthly", "direction": "higher_better"},
         "aliases": ["monthly_recurring_revenue", "recurring_revenue"]},
        {"name": "churn_rate", "label": "Churn Rate", "category": "retention",
         "definition": "Percentage of customers who cancel",
         "formula": {"type": "ratio", "numerator": "churned_customers", "denominator": "total_customers"},
         "target": {"value": 0.03, "unit": "ratio", "period": "monthly", "direction": "lower_better"},
         "aliases": ["churn", "cancellation_rate"]},
        {"name": "ltv", "label": "Customer Lifetime Value", "category": "revenue",
         "definition": "Total revenue expected from a customer over their lifetime",
         "formula": {"type": "calculated", "expression": "arpu * (1 / churn_rate)"},
         "target": {"value": 50000, "unit": "EUR", "direction": "higher_better"},
         "aliases": ["lifetime_value", "clv", "customer_lifetime_value"]},
        {"name": "activation_rate", "label": "Activation Rate", "category": "growth",
         "definition": "Percentage of new users who reach activation milestone",
         "formula": {"type": "ratio", "numerator": "activated_users", "denominator": "new_signups"},
         "target": {"value": 0.6, "unit": "ratio", "direction": "higher_better"},
         "aliases": ["activation", "onboarding_completion"]},
    ],
    departments=[
        {"name": "Engineering", "roles": ["VP Engineering", "Tech Lead", "Senior Engineer", "Engineer"]},
        {"name": "Product", "roles": ["Product Manager", "Product Designer", "UX Researcher"]},
        {"name": "Sales", "roles": ["Account Executive", "SDR", "Sales Manager"]},
        {"name": "Customer Success", "roles": ["CS Manager", "CSM", "Support Engineer"]},
    ],
    recommended_agents=[
        {"name": "Growth Intelligence Agent", "role": "Track MRR, churn, activation, and expansion revenue"},
        {"name": "Customer Health Agent", "role": "Monitor usage patterns, predict churn, identify upsell opportunities"},
        {"name": "Product Analytics Agent", "role": "Track feature adoption, user engagement, and funnels"},
    ],
    terminology=[
        {"term": "MRR", "definition": "Monthly Recurring Revenue", "aliases": ["mrr", "monthly_recurring"]},
        {"term": "ARR", "definition": "Annual Recurring Revenue", "aliases": ["arr", "annual_recurring"]},
        {"term": "Churn", "definition": "Customer cancellation rate", "aliases": ["churn", "churn_rate", "cancellation"]},
        {"term": "LTV", "definition": "Customer Lifetime Value", "aliases": ["ltv", "lifetime_value", "clv"]},
    ],
)

CONSTRUCTION = IndustryTemplate(
    industry="construction",
    description="Construction project management and operations",
    entities=[
        {"entity_type": "project", "label": "Construction Project", "aliases": ["site", "job", "contract"],
         "properties_schema": {"fields": [{"name": "project_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "budget", "type": "currency"}, {"name": "status", "type": "category"}]}},
        {"entity_type": "crew", "label": "Crew", "aliases": ["team", "gang", "workforce"],
         "properties_schema": {"fields": [{"name": "crew_id", "type": "identifier"}, {"name": "foreman", "type": "text"}, {"name": "size", "type": "numeric"}]}},
        {"entity_type": "material", "label": "Construction Material", "aliases": ["supply", "component", "resource"],
         "properties_schema": {"fields": [{"name": "material_id", "type": "identifier"}, {"name": "name", "type": "text"}, {"name": "unit_cost", "type": "currency"}]}},
        {"entity_type": "equipment", "label": "Construction Equipment", "aliases": ["machinery", "plant", "vehicle"],
         "properties_schema": {"fields": [{"name": "equipment_id", "type": "identifier"}, {"name": "type", "type": "category"}, {"name": "status", "type": "category"}]}},
    ],
    kpis=[
        {"name": "schedule_performance", "label": "Schedule Performance Index", "category": "operations",
         "definition": "Earned value / Planned value",
         "formula": {"type": "ratio", "numerator": "earned_value", "denominator": "planned_value"},
         "target": {"value": 1.0, "unit": "index", "direction": "higher_better"},
         "aliases": ["spi", "schedule_index"]},
        {"name": "cost_performance", "label": "Cost Performance Index", "category": "cost",
         "definition": "Earned value / Actual cost",
         "formula": {"type": "ratio", "numerator": "earned_value", "denominator": "actual_cost"},
         "target": {"value": 1.0, "unit": "index", "direction": "higher_better"},
         "aliases": ["cpi", "cost_index"]},
        {"name": "safety_incident_rate", "label": "Safety Incident Rate", "category": "safety",
         "definition": "Recordable incidents per 200,000 work hours",
         "formula": {"type": "calculated", "expression": "incidents * 200000 / hours_worked"},
         "target": {"value": 0, "unit": "incidents", "direction": "lower_better"},
         "aliases": ["incident_rate", "safety_rate", "trir"]},
    ],
    departments=[
        {"name": "Project Management", "roles": ["Project Manager", "Site Supervisor", "Project Engineer"]},
        {"name": "Estimating", "roles": ["Chief Estimator", "Estimator", "Quantity Surveyor"]},
        {"name": "Safety", "roles": ["Safety Manager", "Safety Officer"]},
        {"name": "Operations", "roles": ["Operations Manager", "Superintendent", "Foreman"]},
    ],
    recommended_agents=[
        {"name": "Project Intelligence Agent", "role": "Monitor schedule, budget, and progress across projects"},
        {"name": "Safety Intelligence Agent", "role": "Track incidents, compliance, and safety metrics"},
        {"name": "Cost Intelligence Agent", "role": "Monitor CPI, cost overruns, and resource utilization"},
    ],
    terminology=[
        {"term": "SPI", "definition": "Schedule Performance Index", "aliases": ["spi", "schedule_performance"]},
        {"term": "CPI", "definition": "Cost Performance Index", "aliases": ["cpi", "cost_performance"]},
        {"term": "BIM", "definition": "Building Information Modeling", "aliases": ["bim", "building_model"]},
    ],
)


class IndustryTemplateRegistry:
    """Registry of all industry templates."""

    def __init__(self):
        self._templates: dict[str, IndustryTemplate] = {}
        self._register_defaults()

    def _register_defaults(self):
        for template in [MANUFACTURING, RETAIL, FINANCE, HEALTHCARE, LOGISTICS, SAAS, CONSTRUCTION]:
            self._templates[template.industry] = template

    def get_template(self, industry: str) -> IndustryTemplate | None:
        return self._templates.get(industry.lower())

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    def get_template_dict(self, industry: str) -> dict | None:
        template = self.get_template(industry)
        return template.to_dict() if template else None

    def list_all_templates(self) -> list[dict]:
        return [
            {"industry": t.industry, "description": t.description,
             "entity_count": len(t.entities), "kpi_count": len(t.kpis),
             "agent_count": len(t.recommended_agents)}
            for t in self._templates.values()
        ]

    def register_template(self, template: IndustryTemplate):
        """Register a custom industry template."""
        self._templates[template.industry] = template
        logger.info("Registered template for industry: %s", template.industry)
