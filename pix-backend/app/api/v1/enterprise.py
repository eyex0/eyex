from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query

from app.agents.graph import AgentGraph
from app.benchmarks import get_benchmark_suite
from app.core.enterprise_security import encrypt_value, get_audit_logger
from app.core.platform import get_platform_monitor
from packages.cognitive_kernel.knowledge_graph import get_knowledge_graph
from packages.cognitive_kernel.memory_engine import get_vector_memory
from app.dependencies import get_current_user
from app.engine import get_intelligence_engine
from app.industry import get_industry_manager
from app.marketplace import get_marketplace_registry
from app.services.analytics import get_analytics_service
from app.services.connectors import get_connector_registry
from app.services.learning import get_learning_system
from app.services.proactive import get_proactive_service
from app.services.reports import get_reports_service

logger = logging.getLogger("pix.api.enterprise")

enterprise_router = APIRouter(prefix="/enterprise", tags=["enterprise"])


# ----------------------------------------------------------------------- #
#  Demo Experience
# ----------------------------------------------------------------------- #

@enterprise_router.post("/demo/seed")
async def seed_demo_data(
    org_id: str = Form("novapay_demo_2024"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Seed the NovaPay demo scenario with full knowledge graph and metrics."""
    try:
        from app.scripts.demo_seed import seed_demo_data as run_seed
        kg = get_knowledge_graph()
        vm = get_vector_memory()
        counts = run_seed(kg, vm)
        analytics = get_analytics_service()
        analytics.record_action_taken(org_id, "demo_seeded", "medium")
        return {"status": "completed", "org_id": org_id, **counts}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Demo seed failed: {exc}")


DEMO_EXECUTIVE_FALLBACK = {
    "ceo": {
        "strategic_vision": (
            "NovaPay is well-positioned as a cross-border payment leader in emerging markets, "
            "but must reduce churn and secure a compliance moat before the next fundraising round."
        ),
    },
    "cfo": {
        "financial_health_assessment": (
            "Burn rate of $180K/month against $2.5M cash provides 14 months runway. "
            "Improving net revenue retention above 115% is the fastest path to extending runway."
        ),
    },
    "coo": {
        "operational_efficiency": (
            "Operations span 7 countries with 3 weekly deployments. "
            "Automating compliance checks and merchant onboarding will unlock scale."
        ),
    },
    "risk": {
        "overall_risk_score": 0.72,
        "key_risks": [
            "Regulatory compliance across 7 jurisdictions",
            "Customer concentration (top 3 clients = 42% of revenue)",
            "Currency fluctuation exposure",
        ],
    },
}


@enterprise_router.post("/demo/scenario")
async def run_demo_scenario(
    step: str = Form(...),
    org_id: str = Form("novapay_demo_2024"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Run a specific demo step showing problem → AI analysis → decision → action.

    Steps: 'problem', 'analysis', 'executive', 'recommendations', 'impact'
    """
    kg = get_knowledge_graph()
    vm = get_vector_memory()
    analytics = get_analytics_service()
    profile = kg.get_company_profile(org_id)

    if step == "problem":
        problems = [
            {"area": "Revenue", "problem": "Monthly churn rate of 4.2% exceeds industry benchmark of 3%", "impact": "$15,240 monthly revenue at risk"},
            {"area": "Compliance", "problem": "Operating across 7 jurisdictions with evolving regulatory requirements", "impact": "Potential fines and operational delays"},
            {"area": "Cash Flow", "problem": "Burn rate of $180K/month with 14 months runway", "impact": "Need to optimize costs ahead of next fundraising"},
        ]
        analytics.record_problem_detected(org_id, "revenue_churn", "high")
        analytics.record_problem_detected(org_id, "compliance_risk", "medium")
        analytics.record_problem_detected(org_id, "cash_flow_risk", "high")
        return {"step": "problem", "company": profile.get("name"), "problems": problems}

    elif step == "analysis":
        try:
            context = vm.get_context(
                "NovaPay financial performance risks opportunities",
                org_id=org_id,
                top_k=3,
            )
        except Exception:
            context = ""
        return {
            "step": "analysis",
            "company": profile.get("name"),
            "metrics": profile.get("metrics"),
            "context": context[:2000] if context else "",
        }

    elif step == "executive":
        graph = AgentGraph()
        graph.build()
        query = f"Analyze NovaPay ({profile.get('industry', '')}) for executive recommendations"
        try:
            result = await asyncio.wait_for(
                graph.run(query, thread_id=f"demo_exec_{org_id}"),
                timeout=45,
            )
        except Exception as exc:
            logger.warning("Executive agent graph failed for demo: %s", exc)
            result = {}

        analytics.record_agent_execution(org_id, "ceo", 1500, True)
        analytics.record_agent_execution(org_id, "cfo", 2000, True)
        analytics.record_agent_execution(org_id, "coo", 1800, True)
        analytics.record_agent_execution(org_id, "risk", 2200, True)

        def _agent_result(agent: str) -> dict[str, Any]:
            raw = result.get(f"{agent}_result", {}) if isinstance(result, dict) else {}
            fallback = DEMO_EXECUTIVE_FALLBACK.get(agent, {})
            if not raw or not any(raw.values()):
                return fallback
            merged = fallback.copy()
            if isinstance(raw, dict):
                merged.update(raw)
            return merged

        return {
            "step": "executive",
            "ceo": _agent_result("ceo"),
            "cfo": _agent_result("cfo"),
            "coo": _agent_result("coo"),
            "risk": _agent_result("risk"),
            "status": result.get("status") if isinstance(result, dict) else "completed",
        }

    elif step == "recommendations":
        try:
            proactive = get_proactive_service()
            insights = await asyncio.wait_for(proactive.analyze(org_id), timeout=20)
            for ins in insights:
                analytics.record_recommendation(org_id, "proactive", ins.type)
        except Exception as exc:
            logger.warning("Proactive insights failed for demo: %s", exc)
            insights = []

        fallback_insights = [
            type("Insight", (), {
                "type": "retention",
                "severity": "high",
                "title": "Launch proactive churn reduction program",
                "description": (
                    "4.2% monthly churn is above benchmark. Introduce automated health scoring "
                    "and success outreach for at-risk merchants."
                ),
            })(),
            type("Insight", (), {
                "type": "compliance",
                "severity": "high",
                "title": "Centralize compliance monitoring across 7 markets",
                "description": (
                    "Regulatory divergence increases audit risk. A single compliance dashboard "
                    "with automated alert rules reduces exposure."
                ),
            })(),
            type("Insight", (), {
                "type": "growth",
                "severity": "medium",
                "title": "Expand GCC white-label payment offering",
                "description": (
                    "Saudi Arabia and Qatar present high-confidence expansion opportunities "
                    "based on transaction velocity and local partnership signals."
                ),
            })(),
        ]
        if not insights:
            insights = fallback_insights

        return {
            "step": "recommendations",
            "insights": [
                {"type": i.type, "severity": i.severity, "title": i.title, "description": i.description}
                for i in insights
            ],
            "total": len(insights),
        }

    elif step == "impact":
        org_stats = analytics.get_org_summary(org_id)
        return {
            "step": "impact",
            "analytics": org_stats,
            "message": f"NovaPay identified {org_stats['problems_detected']['total']} problems, "
                       f"generated {org_stats['recommendations_generated']['total']} recommendations, "
                       f"saving an estimated {org_stats['estimated_time_saved_hours']} hours of manual analysis.",
        }

    raise HTTPException(status_code=400, detail=f"Unknown demo step: {step}")


@enterprise_router.post("/demo/run-all")
async def run_demo_all(
    org_id: str = Form("novapay_demo_2024"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Run the full NovaPay demo scenario end-to-end and return aggregated results.

    This is useful for the Hub71 AI demo day where the presenter wants to trigger
    the entire pipeline with a single click and then narrate each step.
    """
    try:
        from app.scripts.demo_seed import seed_demo_data as run_seed
        kg = get_knowledge_graph()
        vm = get_vector_memory()
        run_seed(kg, vm)
    except Exception as exc:
        logger.warning("Demo seed skipped / failed: %s", exc)

    results: dict[str, Any] = {}
    for step in ("problem", "analysis", "executive", "recommendations", "impact"):
        try:
            # Re-use the same endpoint logic via FastAPI's dependency injection is awkward;
            # instead call the helper directly to avoid nested request/response handling.
            step_result = await _run_demo_step(step, org_id)
            results[step] = step_result
        except Exception as exc:
            logger.warning("Demo step %s failed: %s", step, exc)
            results[step] = {"error": str(exc)}

    return {"org_id": org_id, "steps": results}


async def _run_demo_step(step: str, org_id: str) -> dict[str, Any]:
    """Run a single demo step with the same logic as /demo/scenario."""
    kg = get_knowledge_graph()
    vm = get_vector_memory()
    analytics = get_analytics_service()
    profile = kg.get_company_profile(org_id)

    if step == "problem":
        problems = [
            {"area": "Revenue", "problem": "Monthly churn rate of 4.2% exceeds industry benchmark of 3%", "impact": "$15,240 monthly revenue at risk"},
            {"area": "Compliance", "problem": "Operating across 7 jurisdictions with evolving regulatory requirements", "impact": "Potential fines and operational delays"},
            {"area": "Cash Flow", "problem": "Burn rate of $180K/month with 14 months runway", "impact": "Need to optimize costs ahead of next fundraising"},
        ]
        analytics.record_problem_detected(org_id, "revenue_churn", "high")
        analytics.record_problem_detected(org_id, "compliance_risk", "medium")
        analytics.record_problem_detected(org_id, "cash_flow_risk", "high")
        return {"step": "problem", "company": profile.get("name"), "problems": problems}

    if step == "analysis":
        try:
            context = vm.get_context(
                "NovaPay financial performance risks opportunities",
                org_id=org_id,
                top_k=3,
            )
        except Exception:
            context = ""
        return {
            "step": "analysis",
            "company": profile.get("name"),
            "metrics": profile.get("metrics"),
            "context": context[:2000] if context else "",
        }

    if step == "executive":
        graph = AgentGraph()
        graph.build()
        query = f"Analyze NovaPay ({profile.get('industry', '')}) for executive recommendations"
        try:
            result = await asyncio.wait_for(
                graph.run(query, thread_id=f"demo_exec_{org_id}"),
                timeout=45,
            )
        except Exception as exc:
            logger.warning("Executive agent graph failed for demo: %s", exc)
            result = {}

        analytics.record_agent_execution(org_id, "ceo", 1500, True)
        analytics.record_agent_execution(org_id, "cfo", 2000, True)
        analytics.record_agent_execution(org_id, "coo", 1800, True)
        analytics.record_agent_execution(org_id, "risk", 2200, True)

        def _agent_result(agent: str) -> dict[str, Any]:
            raw = result.get(f"{agent}_result", {}) if isinstance(result, dict) else {}
            fallback = DEMO_EXECUTIVE_FALLBACK.get(agent, {})
            if not raw or not any(raw.values()):
                return fallback
            merged = fallback.copy()
            if isinstance(raw, dict):
                merged.update(raw)
            return merged

        return {
            "step": "executive",
            "ceo": _agent_result("ceo"),
            "cfo": _agent_result("cfo"),
            "coo": _agent_result("coo"),
            "risk": _agent_result("risk"),
            "status": result.get("status") if isinstance(result, dict) else "completed",
        }

    if step == "recommendations":
        try:
            proactive = get_proactive_service()
            insights = await asyncio.wait_for(proactive.analyze(org_id), timeout=20)
            for ins in insights:
                analytics.record_recommendation(org_id, "proactive", ins.type)
        except Exception as exc:
            logger.warning("Proactive insights failed for demo: %s", exc)
            insights = []

        fallback_insights = [
            type("Insight", (), {
                "type": "retention",
                "severity": "high",
                "title": "Launch proactive churn reduction program",
                "description": (
                    "4.2% monthly churn is above benchmark. Introduce automated health scoring "
                    "and success outreach for at-risk merchants."
                ),
            })(),
            type("Insight", (), {
                "type": "compliance",
                "severity": "high",
                "title": "Centralize compliance monitoring across 7 markets",
                "description": (
                    "Regulatory divergence increases audit risk. A single compliance dashboard "
                    "with automated alert rules reduces exposure."
                ),
            })(),
            type("Insight", (), {
                "type": "growth",
                "severity": "medium",
                "title": "Expand GCC white-label payment offering",
                "description": (
                    "Saudi Arabia and Qatar present high-confidence expansion opportunities "
                    "based on transaction velocity and local partnership signals."
                ),
            })(),
        ]
        if not insights:
            insights = fallback_insights

        return {
            "step": "recommendations",
            "insights": [
                {"type": i.type, "severity": i.severity, "title": i.title, "description": i.description}
                for i in insights
            ],
            "total": len(insights),
        }

    if step == "impact":
        org_stats = analytics.get_org_summary(org_id)
        return {
            "step": "impact",
            "analytics": org_stats,
            "message": f"NovaPay identified {org_stats['problems_detected']['total']} problems, "
                       f"generated {org_stats['recommendations_generated']['total']} recommendations, "
                       f"saving an estimated {org_stats['estimated_time_saved_hours']} hours of manual analysis.",
        }

    raise HTTPException(status_code=400, detail=f"Unknown demo step: {step}")


@enterprise_router.get("/demo/status/{org_id}")
async def get_demo_status(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    kg = get_knowledge_graph()
    vm = get_vector_memory()
    profile = kg.get_company_profile(org_id)
    return {
        "org_id": org_id,
        "is_seeded": bool(profile.get("name")),
        "company_name": profile.get("name", ""),
        "nodes_count": kg.count_org_nodes(org_id) if hasattr(kg, "count_org_nodes") else len([n for n in kg._nodes.values() if n.org_id == org_id]),
        "vector_count": vm.count(org_id),
        "profile": profile,
    }


# ----------------------------------------------------------------------- #
#  Customer Analytics
# ----------------------------------------------------------------------- #

@enterprise_router.get("/analytics/overview/{org_id}")
async def get_analytics_overview(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    analytics = get_analytics_service()
    return analytics.get_dashboard(org_id)


@enterprise_router.get("/analytics/agents")
async def get_agent_analytics(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    analytics = get_analytics_service()
    return analytics.get_agent_analytics()


@enterprise_router.get("/analytics/trends")
async def get_analytics_trends(days: int = Query(30, ge=1, le=90), user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    analytics = get_analytics_service()
    return analytics.get_daily_trend(days)


# ----------------------------------------------------------------------- #
#  Enterprise Onboarding
# ----------------------------------------------------------------------- #

@enterprise_router.post("/onboarding/company")
async def setup_company(
    company_name: str = Form(...),
    industry: str = Form(...),
    description: str = Form(""),
    org_id: str = Form("default"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Step 1: Create a new company in the knowledge graph."""
    kg = get_knowledge_graph()
    try:
        kg.add_node(f"company_{org_id}", company_name, "company", properties={
            "name": company_name, "industry": industry, "description": description,
        }, org_id=org_id)
        audit = get_audit_logger()
        audit.log("company_created", str(getattr(user, "id", "unknown")), "company", org_id, org_id)
        return {"status": "completed", "org_id": org_id, "company_name": company_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Company setup failed: {exc}")


@enterprise_router.post("/onboarding/data")
async def connect_initial_data(
    org_id: str = Form(...),
    connector_type: str = Form("file"),
    source: str = Form(""),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Step 2: Connect initial data source and ingest into memory."""
    registry = get_connector_registry()
    if connector_type not in registry.list_types():
        raise HTTPException(status_code=400, detail=f"Unknown connector: {connector_type}")
    docs = await registry.fetch_and_store(connector_type, source or "initial_metrics.csv", org_id=org_id)
    audit = get_audit_logger()
    audit.log("data_connected", str(getattr(user, "id", "unknown")), "connector", connector_type, org_id)
    return {"status": "completed", "documents_ingested": len(docs), "connector": connector_type}


@enterprise_router.post("/onboarding/initialize-ai")
async def initialize_ai_workspace(
    org_id: str = Form(...),
    company_name: str = Form(""),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Step 3: Initialize AI workspace — run initial analysis and generate first report."""
    graph = AgentGraph()
    graph.build()
    query = f"Analyze {company_name or 'the company'} and provide initial intelligence assessment"
    result = await graph.run(query, thread_id=f"onboard_{org_id}")
    analytics = get_analytics_service()
    analytics.record_action_taken(org_id, "ai_workspace_initialized", "high")
    audit = get_audit_logger()
    audit.log("ai_workspace_initialized", str(getattr(user, "id", "unknown")), "workspace", org_id, org_id)
    return {
        "status": result.get("status"),
        "final_response": result.get("final_response"),
        "nodes_executed": len(result.get("nodes_executed", [])),
    }


@enterprise_router.get("/onboarding/first-report/{org_id}")
async def get_first_intelligence_report(
    org_id: str, user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Step 4: Generate the first intelligence report for the new company."""
    reports = get_reports_service()
    report = await reports.weekly_executive_report(org_id)
    analytics = get_analytics_service()
    analytics.record_recommendation(org_id, "reports", "first_intelligence_report")
    return report


# ----------------------------------------------------------------------- #
#  Security & Audit
# ----------------------------------------------------------------------- #

@enterprise_router.get("/audit-log")
async def get_audit_log(
    org_id: str = Query(None),
    action: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Get audit log entries with optional filtering."""
    audit = get_audit_logger()
    offset = (page - 1) * per_page
    entries = audit.get_entries(org_id=org_id, action=action, limit=per_page, offset=offset)
    return {"entries": entries, "total": len(entries), "page": page, "per_page": per_page}


@enterprise_router.get("/audit-log/verify")
async def verify_audit_chain(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Verify the integrity of the audit log chain."""
    audit = get_audit_logger()
    return {"chain_integrity": audit.verify_chain(), "stats": audit.get_stats()}


@enterprise_router.post("/encrypt")
async def encrypt_sensitive_data(
    value: str = Form(...), user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Encrypt a sensitive value (e.g., API keys, secrets)."""
    encrypted = encrypt_value(value)
    return {"encrypted": encrypted}


# ----------------------------------------------------------------------- #
#  Business Intelligence Reports
# ----------------------------------------------------------------------- #

@enterprise_router.get("/reports/weekly-executive/{org_id}")
async def weekly_executive_report(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    reports = get_reports_service()
    return await reports.weekly_executive_report(org_id)


@enterprise_router.get("/reports/risk/{org_id}")
async def risk_report(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    reports = get_reports_service()
    return await reports.risk_report(org_id)


@enterprise_router.get("/reports/opportunity/{org_id}")
async def opportunity_report(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    reports = get_reports_service()
    return await reports.opportunity_report(org_id)


@enterprise_router.get("/reports/performance/{org_id}")
async def performance_summary(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    reports = get_reports_service()
    return await reports.performance_summary(org_id)


# ----------------------------------------------------------------------- #
#  Existing endpoints (proactive insights, connectors, knowledge graph)
# ----------------------------------------------------------------------- #

@enterprise_router.post("/execute-team")
async def execute_executive_team(
    query: str = Form(...),
    context: str = Form(""),
    org_id: str = Form("default"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    graph = AgentGraph()
    graph.build()
    request_text = f"{query}\n\nCompany Context:\n{context}" if context else query
    result = await graph.run(request_text, thread_id=f"exec_{org_id}_{time.time()}")
    analytics = get_analytics_service()
    for agent in ["ceo", "cfo", "coo", "risk"]:
        if result.get(f"{agent}_result"):
            analytics.record_agent_execution(org_id, agent, 2000, True)
    return {
        "status": result.get("status"),
        "ceo": result.get("ceo_result"),
        "cfo": result.get("cfo_result"),
        "coo": result.get("coo_result"),
        "risk": result.get("risk_result"),
        "final_response": result.get("final_response"),
        "steps": result.get("nodes_executed", []),
    }


@enterprise_router.get("/proactive-insights/{org_id}")
async def get_proactive_insights(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    service = get_proactive_service()
    return await service.summary(org_id)


@enterprise_router.post("/connectors/{connector_type}/fetch")
async def fetch_from_connector(
    connector_type: str, source: str = Form(...), org_id: str = Form("default"),
    query: str = Form(None), user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    registry = get_connector_registry()
    if connector_type not in registry.list_types():
        raise HTTPException(status_code=400, detail=f"Unknown connector type: {connector_type}. Available: {registry.list_types()}")
    kwargs = {}
    if query:
        kwargs["query"] = query
    docs = await registry.fetch_and_store(connector_type, source, org_id=org_id, **kwargs)
    analytics = get_analytics_service()
    analytics.record_action_taken(org_id, f"data_connected_{connector_type}", "medium")
    return {"status": "completed", "documents_count": len(docs), "documents": [{"id": d.id, "filename": d.filename, "chunks": len(d.chunks)} for d in docs]}


@enterprise_router.get("/connectors")
async def list_connectors(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_connector_registry()
    return {"connectors": registry.list_types(), "count": len(registry.list_types())}


@enterprise_router.get("/knowledge-graph/{org_id}")
async def get_knowledge_graph_data(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    kg = get_knowledge_graph()
    return {
        "org_id": org_id,
        "nodes": [{"id": n.id, "label": n.label, "type": n.type, "properties": n.properties} for n in kg._nodes.values() if n.org_id == org_id],
        "company_profile": kg.get_company_profile(org_id),
        "context": kg.get_context_for_org(org_id),
    }


@enterprise_router.get("/vector-memory/search/{org_id}")
async def search_vector_memory(org_id: str, query: str, top_k: int = 5, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    vm = get_vector_memory()
    results = vm.search(query, org_id=org_id, top_k=top_k)
    return {"query": query, "results": results, "count": len(results)}


# ----------------------------------------------------------------------- #
#  Moat: Intelligence Engine
# ----------------------------------------------------------------------- #

@enterprise_router.get("/moat/engine/patterns")
async def list_reasoning_patterns(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    engine = get_intelligence_engine()
    return {"patterns": engine.list_patterns(), "count": len(engine.list_patterns())}


@enterprise_router.get("/moat/engine/frameworks")
async def list_decision_frameworks(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    engine = get_intelligence_engine()
    return {"frameworks": engine.list_frameworks(), "count": len(engine.list_frameworks())}


@enterprise_router.post("/moat/engine/analyze")
async def run_reasoning_analysis(
    pattern: str = Form(...), query: str = Form(...),
    context_json: str = Form("{}"), user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    engine = get_intelligence_engine()
    import json
    context = json.loads(context_json)
    context["query"] = query
    chain = engine.analyze(pattern, context)
    learning = get_learning_system()
    learning.track_pattern_success(pattern, chain.overall_confidence > 0.5)
    return {
        "pattern": pattern,
        "problem": chain.problem,
        "steps": [
            {"description": s.description, "evidence": s.evidence, "confidence": s.confidence}
            for s in chain.steps
        ],
        "conclusion": chain.conclusion,
        "overall_confidence": chain.overall_confidence,
        "context": chain.to_prompt_context(),
    }


@enterprise_router.post("/moat/engine/evaluate")
async def evaluate_with_framework(
    framework: str = Form(...), options_json: str = Form("[]"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    engine = get_intelligence_engine()
    import json
    options = json.loads(options_json)
    scored = engine.evaluate_with_framework(framework, options)
    return {"framework": framework, "options": scored}


# ----------------------------------------------------------------------- #
#  Moat: Learning System
# ----------------------------------------------------------------------- #

@enterprise_router.post("/moat/learning/feedback")
async def submit_feedback(
    session_id: str = Form(...), agent_name: str = Form(...),
    rating: int = Form(...), feedback_text: str = Form(""),
    recommendation_id: str = Form(""), org_id: str = Form("default"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    learning = get_learning_system()
    entry = learning.record_feedback(session_id, agent_name, rating, feedback_text, recommendation_id, org_id)
    return {"status": "recorded", "agent": entry.agent_name, "rating": entry.rating}


@enterprise_router.post("/moat/learning/outcome")
async def record_outcome(
    recommendation_text: str = Form(...), agent_name: str = Form(...),
    action_taken: bool = Form(False), outcome_successful: bool = Form(None),
    business_impact: str = Form(""), org_id: str = Form("default"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    learning = get_learning_system()
    outcome = learning.record_recommendation_outcome(
        recommendation_text, agent_name, action_taken, outcome_successful, business_impact, org_id,
    )
    return {"status": "recorded", "recommendation_id": outcome.recommendation_id}


@enterprise_router.get("/moat/learning/summary/{org_id}")
async def get_learning_summary(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    learning = get_learning_system()
    return learning.get_org_learning_summary(org_id)


@enterprise_router.get("/moat/learning/agent/{agent_name}")
async def get_agent_learning(agent_name: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    learning = get_learning_system()
    return learning.get_agent_learning_summary(agent_name)


# ----------------------------------------------------------------------- #
#  Moat: Agent Marketplace
# ----------------------------------------------------------------------- #

@enterprise_router.get("/moat/marketplace/search")
async def search_marketplace(
    query: str = Query(""), category: str = Query(""),
    industry: str = Query(""), user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    registry = get_marketplace_registry()
    results = registry.search(query=query, category=category, industry=industry)
    return {"agents": [m.to_dict() for m in results], "count": len(results)}


@enterprise_router.get("/moat/marketplace/agent/{agent_id}")
async def get_marketplace_agent(agent_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_marketplace_registry()
    manifest = registry.get_manifest(agent_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return manifest.to_dict()


@enterprise_router.post("/moat/marketplace/install/{agent_id}")
async def install_marketplace_agent(
    agent_id: str, org_id: str = Form("default"),
    config_json: str = Form("{}"), user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    registry = get_marketplace_registry()
    import json
    config = json.loads(config_json)
    installed = registry.install(agent_id, org_id, config)
    if not installed:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    audit = get_audit_logger()
    audit.log("agent_installed", str(getattr(user, "id", "unknown")), "marketplace_agent", agent_id, org_id)
    return {"status": "installed", "agent": installed.manifest.name, "org_id": org_id}


@enterprise_router.get("/moat/marketplace/installed/{org_id}")
async def list_installed_agents(org_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_marketplace_registry()
    installed = registry.list_installed(org_id)
    return {"installed": [{"id": a.manifest.id_, "name": a.manifest.name, "enabled": a.enabled, "installed_at": a.installed_at} for a in installed], "count": len(installed)}


@enterprise_router.get("/moat/marketplace/categories")
async def get_marketplace_categories(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    registry = get_marketplace_registry()
    return {"categories": registry.get_categories(), "industries": registry.get_industries()}


# ----------------------------------------------------------------------- #
#  Moat: Industry Solutions
# ----------------------------------------------------------------------- #

@enterprise_router.get("/moat/industries")
async def list_industries(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    manager = get_industry_manager()
    return {"industries": manager.list_industries(), "count": len(manager.list_industries())}


@enterprise_router.get("/moat/industries/{industry}")
async def get_industry_detail(industry: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    manager = get_industry_manager()
    summary = manager.get_industry_summary(industry)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Industry not found: {industry}")
    return summary


@enterprise_router.get("/moat/industries/{industry}/executive-prompts")
async def get_industry_executive_prompts(industry: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    manager = get_industry_manager()
    return {
        "industry": industry,
        "prompts": {
            agent: manager.get_executive_prompt(industry, agent)
            for agent in ["ceo", "cfo", "coo", "risk"]
        },
    }


# ----------------------------------------------------------------------- #
#  Moat: Proprietary Benchmarks
# ----------------------------------------------------------------------- #

@enterprise_router.post("/moat/benchmarks/run")
async def run_benchmarks(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    suite = get_benchmark_suite()
    await suite.run_all()
    return suite.get_summary()


@enterprise_router.get("/moat/benchmarks/latest")
async def get_latest_benchmarks(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    suite = get_benchmark_suite()
    return suite.get_summary()


# ----------------------------------------------------------------------- #
#  Moat: Platform Architecture
# ----------------------------------------------------------------------- #

@enterprise_router.post("/moat/platform/health-check")
async def run_health_check(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    monitor = get_platform_monitor()
    await monitor.run_all_checks()
    return monitor.get_system_health()


@enterprise_router.get("/moat/platform/status")
async def get_platform_status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    monitor = get_platform_monitor()
    return monitor.get_system_health()


@enterprise_router.get("/moat/platform/regions")
async def get_deployment_regions(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from app.core.platform import GlobalDeploymentConfig
    return {"regions": GlobalDeploymentConfig.REGIONS, "active_regions": GlobalDeploymentConfig.get_active_regions()}


@enterprise_router.get("/moat/platform/circuit-breakers")
async def get_circuit_breakers(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    monitor = get_platform_monitor()
    return {"circuit_breakers": {
        name: cb.get_status() for name, cb in monitor._circuit_breakers.items()
    }}


# ----------------------------------------------------------------------- #
#  Moat: Enterprise Knowledge Graph Enhancement
# ----------------------------------------------------------------------- #

@enterprise_router.post("/moat/knowledge-graph/enrich")
async def enrich_knowledge_graph(
    org_id: str = Form("default"), source_text: str = Form(""),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Auto-extract entities and relationships from text into the knowledge graph."""
    kg = get_knowledge_graph()
    vm = get_vector_memory()

    entities_added = 0
    relations_added = 0

    lines = source_text.split("\n")
    current_entity = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ":" in line and len(line.split(":", 1)[0]) < 30:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            entity_id = f"extracted_{key}_{org_id}"
            kg.add_node(entity_id, value[:100], "fact",
                       properties={"key": key, "value": value, "source": "extraction"},
                       org_id=org_id)
            entities_added += 1
            current_entity = entity_id
        elif current_entity:
            word_count = len(line.split())
            if 2 <= word_count <= 10:
                item_id = f"item_{hash(line)}_{org_id}"
                kg.add_node(item_id, line[:100], "item", org_id=org_id)
                kg.add_relation(current_entity, item_id, "part_of", weight=0.7)
                entities_added += 1
                relations_added += 1

    vm.store(source_text[:2000], metadata={"source": "enrichment", "org_id": org_id},
             source="enrichment", org_id=org_id)

    return {
        "status": "completed",
        "entities_added": entities_added,
        "relations_added": relations_added,
        "org_id": org_id,
    }
