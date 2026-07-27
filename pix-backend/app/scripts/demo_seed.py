from __future__ import annotations

import logging

from packages.cognitive_kernel.knowledge_graph import get_knowledge_graph
from packages.cognitive_kernel.memory_engine.vector_memory import VectorMemory, get_vector_memory

logger = logging.getLogger("pix.scripts.demo_seed")

# Seed realistic demo data for enterprise validation.
# Creates a fictional company "NovaPay" — a fintech startup — with full
# knowledge graph, vector memory, metrics, and a complete demo scenario.

DEMO_ORG_ID = "novapay_demo_2024"

COMPANY_PROFILE = {
    "name": "NovaPay Technologies",
    "industry": "Fintech / Payment Processing",
    "description": "NovaPay is a Series A fintech company building a real-time cross-border payment infrastructure for emerging markets. Founded in 2022, headquartered in Dubai (Hub71), with 45 employees across UAE, Kenya, and India.",
    "founded": "2022",
    "funding_stage": "Series A",
    "total_raised": "$8.5M",
    "last_valuation": "$42M",
    "team_size": 45,
}

METRICS = {
    "monthly_revenue": "$320,000",
    "revenue_growth_rate": "18% MoM",
    "gross_margin": "72%",
    "monthly_active_users": "12,500",
    "total_transactions_volume": "$4.2M/month",
    "average_transaction_value": "$336",
    "customer_acquisition_cost": "$48",
    "customer_lifetime_value": "$1,240",
    "ltv_cac_ratio": "25.8",
    "monthly_churn_rate": "4.2%",
    "net_revenue_retention": "112%",
    "burn_rate": "$180,000/month",
    "runway_months": "14",
    "cash_on_hand": "$2.5M",
    "number_of_enterprise_clients": "18",
    "number_of_smb_clients": "340",
    "countries_operating": "7",
    "employee_satisfaction": "8.2/10",
    "development_velocity": "24 stories/sprint",
    "deployment_frequency": "3x/week",
}

KEY_PEOPLE = [
    {"name": "Aisha Al Maktoum", "role": "CEO & Co-Founder", "background": "Ex-Mastercard, Harvard MBA"},
    {"name": "Ravi Patel", "role": "CTO & Co-Founder", "background": "Ex-Stripe, IIT Delhi"},
    {"name": "Sarah Chen", "role": "CFO", "background": "Ex-Revolut, CPA"},
    {"name": "James Okafor", "role": "COO", "background": "Ex-Flutterwave"},
    {"name": "Dr. Layla Hassan", "role": "Head of Risk & Compliance", "background": "Ex-Central Bank of UAE"},
]

PRODUCTS = [
    "NovaPay API — real-time cross-border payment gateway",
    "NovaCollect — merchant collection and settlement platform",
    "NovaFX — wholesale currency exchange for businesses",
    "NovaInsights — transaction analytics dashboard",
]

COMPETITORS = ["Paystack (Stripe)", "Flutterwave", "Chipper Cash", "DLocal", "Convat (B2B)"]

RISKS = [
    ("Regulatory compliance across 7 jurisdictions", "high"),
    ("Customer concentration: top 3 clients = 42% of revenue", "high"),
    ("Talent retention in competitive fintech market", "medium"),
    ("Currency fluctuation exposure in emerging markets", "medium"),
    ("Infrastructure reliability in regions with frequent outages", "medium"),
]

OPPORTUNITIES = [
    ("BNPL integration for merchant clients", 0.75),
    ("SME lending based on transaction data", 0.7),
    ("GCC expansion (Saudi Arabia, Qatar)", 0.8),
    ("White-label payment solution for banks", 0.65),
    ("AI-powered fraud detection add-on", 0.85),
]


def seed_demo_data(
    kg: KnowledgeGraph | None = None,
    vm: VectorMemory | None = None,
) -> dict[str, int]:
    kg = kg or get_knowledge_graph()
    vm = vm or get_vector_memory()
    counts: dict[str, int] = {"nodes": 0, "relations": 0, "vectors": 0}

    # Company node
    kg.add_node(
        f"company_{DEMO_ORG_ID}", COMPANY_PROFILE["name"], "company",
        properties=COMPANY_PROFILE, org_id=DEMO_ORG_ID,
    )
    counts["nodes"] += 1

    # People nodes
    for person in KEY_PEOPLE:
        kg.add_node(
            f"person_{person['name'].lower().replace(' ', '_')}",
            person["name"], "person",
            properties=person, org_id=DEMO_ORG_ID,
        )
        kg.add_relation(
            f"company_{DEMO_ORG_ID}", f"person_{person['name'].lower().replace(' ', '_')}",
            "reports_to", weight=1.0,
        )
        counts["nodes"] += 1
        counts["relations"] += 1

    # Product nodes
    for product in PRODUCTS:
        pid = f"product_{product.lower().replace(' ', '_').replace('—', '').strip()}"
        kg.add_node(pid, product, "product", org_id=DEMO_ORG_ID)
        kg.add_relation(f"company_{DEMO_ORG_ID}", pid, "generates", weight=1.0)
        counts["nodes"] += 1
        counts["relations"] += 1

    # Competitor nodes
    for comp in COMPETITORS:
        cid = f"competitor_{comp.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('.', '')}"
        kg.add_node(cid, comp, "competitor", org_id=DEMO_ORG_ID)
        kg.add_relation(f"company_{DEMO_ORG_ID}", cid, "competes_with", weight=0.8)
        counts["nodes"] += 1
        counts["relations"] += 1

    # Risk nodes
    for risk_desc, severity in RISKS:
        rid = f"risk_{risk_desc[:30].lower().replace(' ', '_')}"
        kg.add_node(rid, risk_desc, "risk",
                    properties={"severity": severity, "description": risk_desc},
                    org_id=DEMO_ORG_ID)
        counts["nodes"] += 1

    # Metric nodes
    for metric_name, metric_value in METRICS.items():
        mid = f"metric_{metric_name.lower().replace(' ', '_')}"
        kg.add_node(mid, metric_name, "metric",
                    properties={"value": metric_value, "category": _categorize_metric(metric_name)},
                    org_id=DEMO_ORG_ID)
        kg.add_relation(f"company_{DEMO_ORG_ID}", mid, "measured_by", weight=0.9)
        counts["nodes"] += 1
        counts["relations"] += 1

    # Store metrics as vectors for semantic search
    metric_text = "\n".join(f"{k}: {v}" for k, v in METRICS.items())
    vm.store(metric_text, metadata={"type": "company_metrics", "org_id": DEMO_ORG_ID},
             source="seed", org_id=DEMO_ORG_ID)
    counts["vectors"] += 1

    # Store key documents
    documents = [
        ("NovaPay Product Overview", "NovaPay provides real-time cross-border payment infrastructure..."),
        ("Q3 2024 Board Deck", "Revenue grew 18% MoM reaching $320K..."),
        ("Competitive Analysis", "Market positioning vs Paystack, Flutterwave, Chipper Cash..."),
        ("Risk Assessment Report", "Key risks include regulatory compliance across 7 jurisdictions..."),
    ]
    for title, content in documents:
        vm.store(content, metadata={"title": title, "org_id": DEMO_ORG_ID},
                 source="seed", org_id=DEMO_ORG_ID)
        counts["vectors"] += 1

    # Opportunity nodes
    for opp_desc, confidence in OPPORTUNITIES:
        oid = f"opportunity_{opp_desc[:30].lower().replace(' ', '_')}"
        kg.add_node(oid, opp_desc, "opportunity",
                    properties={"confidence": confidence, "description": opp_desc},
                    org_id=DEMO_ORG_ID)
        counts["nodes"] += 1

    # Key relationships
    kg.add_relation("metric_monthly_revenue", "metric_burn_rate", "impacts", weight=0.9)
    kg.add_relation("metric_monthly_churn_rate", "metric_customer_lifetime_value", "impacts", weight=0.85)

    logger.info("Seeded %d nodes, %d relations, %d vectors for org=%s",
                counts["nodes"], counts["relations"], counts["vectors"], DEMO_ORG_ID)
    return counts

def _categorize_metric(name: str) -> str:
    name_lower = name.lower()
    if any(w in name_lower for w in ["revenue", "margin", "burn", "cash", "runway"]):
        return "financial"
    if any(w in name_lower for w in ["user", "customer", "churn", "acquisition", "ltv", "retention"]):
        return "customer"
    if any(w in name_lower for w in ["employee", "satisfaction", "team"]):
        return "hr"
    if any(w in name_lower for w in ["deployment", "development", "sprint"]):
        return "engineering"
    return "business"
