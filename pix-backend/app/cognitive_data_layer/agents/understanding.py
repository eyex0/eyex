from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.cognitive_data_layer.canonical.model import CanonicalDataset
from app.cognitive_data_layer.semantic import SemanticUnderstandingEngine


@dataclass
class AgentState:
    sheets: list[dict[str, Any]]
    dataset: CanonicalDataset | None = None
    insights: dict[str, Any] = None  # type: ignore[assignment]
    quality_report: dict[str, Any] = None  # type: ignore[assignment]
    confidence_report: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.insights is None:
            self.insights = {}
        if self.quality_report is None:
            self.quality_report = {}
        if self.confidence_report is None:
            self.confidence_report = {}


class DataDiscoveryAgent:
    """Identify tables, sheets, and basic structure."""

    def run(self, state: AgentState) -> AgentState:
        summary = []
        for sheet in state.sheets:
            df: pd.DataFrame = sheet["data"]
            summary.append(
                {
                    "name": sheet["name"],
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": list(df.columns),
                }
            )
        state.insights["discovery"] = summary
        return state


class SchemaAnalysisAgent:
    """Detect columns, keys, and relationships."""

    def __init__(self, schema_discoverer: Any) -> None:
        self.schema_discoverer = schema_discoverer

    def run(self, state: AgentState) -> AgentState:
        schemas = {}
        dataframes = {sheet["name"]: sheet["data"] for sheet in state.sheets}
        for sheet in state.sheets:
            discovery = self.schema_discoverer.discover(
                table_name=sheet["name"], df=sheet["data"], all_tables=dataframes
            )
            schemas[sheet["name"]] = {
                "columns": [c.name for c in discovery.columns],
                "primary_keys": discovery.primary_keys,
                "foreign_keys": [
                    {
                        "source": f"{r.source_table}.{r.source_column}",
                        "target": f"{r.target_table}.{r.target_column}",
                    }
                    for r in discovery.foreign_keys
                ],
                "is_time_series": discovery.is_time_series,
                "categories": discovery.categories,
            }
        state.insights["schema"] = schemas
        return state


class BusinessContextAgent:
    """Map columns to canonical business entities."""

    def __init__(self, semantic_engine: SemanticUnderstandingEngine | None = None) -> None:
        self.semantic_engine = semantic_engine or SemanticUnderstandingEngine()

    def run(self, state: AgentState) -> AgentState:
        mappings = {}
        for sheet in state.sheets:
            df: pd.DataFrame = sheet["data"]
            sample_map = {col: df[col].dropna().head(5).tolist() for col in df.columns}
            mappings[sheet["name"]] = [
                {
                    "column": m.column,
                    "entity": m.entity_type.value,
                    "confidence": m.confidence,
                    "explanation": m.explanation,
                }
                for m in self.semantic_engine.batch_infer(list(df.columns), sample_map)
            ]
        state.insights["business_context"] = mappings
        return state


class DataQualityAgent:
    """Detect data quality issues."""

    def __init__(self, quality_engine: Any) -> None:
        self.quality_engine = quality_engine

    def run(self, state: AgentState) -> AgentState:
        all_issues = []
        for sheet in state.sheets:
            df: pd.DataFrame = sheet["data"]
            # Re-build columns with semantic info
            from app.cognitive_data_layer.schema import SchemaDiscoverer

            discovery = SchemaDiscoverer().discover(sheet["name"], df)
            issues = self.quality_engine.analyze(sheet["name"], df, discovery.columns)
            all_issues.extend(issues)
        state.quality_report = self.quality_engine.generate_report(all_issues)
        return state


class MappingValidationAgent:
    """Validate semantic mappings and flag low-confidence ones."""

    def __init__(self, confidence_engine: Any) -> None:
        self.confidence_engine = confidence_engine

    def run(self, state: AgentState) -> AgentState:
        from app.cognitive_data_layer.schema import SchemaDiscoverer

        low_confidence = []
        for sheet in state.sheets:
            df: pd.DataFrame = sheet["data"]
            discovery = SchemaDiscoverer().discover(sheet["name"], df)
            assessments = self.confidence_engine.batch_assess(discovery.columns)
            for col_name, assessment in assessments.items():
                if assessment.needs_clarification:
                    low_confidence.append(
                        {
                            "table": sheet["name"],
                            "column": col_name,
                            "score": assessment.score,
                            "explanation": assessment.explanation,
                        }
                    )
        state.confidence_report = {
            "low_confidence_mappings": low_confidence,
            "count": len(low_confidence),
        }
        return state


class DataUnderstandingSupervisor:
    """Orchestrate data understanding agents sequentially."""

    def __init__(
        self,
        discovery_agent: DataDiscoveryAgent | None = None,
        schema_agent: SchemaAnalysisAgent | None = None,
        context_agent: BusinessContextAgent | None = None,
        quality_agent: DataQualityAgent | None = None,
        validation_agent: MappingValidationAgent | None = None,
    ) -> None:
        self.discovery_agent = discovery_agent or DataDiscoveryAgent()
        self.schema_agent = schema_agent or SchemaAnalysisAgent(None)
        self.context_agent = context_agent or BusinessContextAgent()
        self.quality_agent = quality_agent or DataQualityAgent(None)
        self.validation_agent = validation_agent or MappingValidationAgent(None)

    def run(self, sheets: list[dict[str, Any]]) -> AgentState:
        state = AgentState(sheets=sheets)
        state = self.discovery_agent.run(state)
        state = self.schema_agent.run(state)
        state = self.context_agent.run(state)
        state = self.quality_agent.run(state)
        state = self.validation_agent.run(state)
        return state

    async def arun(self, sheets: list[dict[str, Any]]) -> AgentState:
        return self.run(sheets)
