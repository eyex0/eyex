from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd

from app.cognitive_data_layer.agents import DataUnderstandingSupervisor
from app.cognitive_data_layer.canonical import CanonicalBuilder, CanonicalDataset
from app.cognitive_data_layer.confidence import ConfidenceEngine
from app.cognitive_data_layer.knowledge import KnowledgeGraphIntegration
from app.cognitive_data_layer.learning import CompanyLearningSystem
from app.cognitive_data_layer.parser import parse_source, register_default_parsers
from app.cognitive_data_layer.quality import DataQualityEngine
from app.cognitive_data_layer.schema import SchemaDiscoverer


class CognitiveDataPipeline:
    """End-to-end pipeline for the πX Cognitive Data Layer."""

    def __init__(
        self,
        learning_system: CompanyLearningSystem | None = None,
        confidence_threshold: float = 0.5,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        register_default_parsers()
        self.schema_discoverer = SchemaDiscoverer()
        self.canonical_builder = CanonicalBuilder(self.schema_discoverer)
        self.learning_system = learning_system or CompanyLearningSystem()
        self.confidence_engine = ConfidenceEngine(clarification_threshold=confidence_threshold)
        self.quality_engine = DataQualityEngine()
        self.knowledge_graph = KnowledgeGraphIntegration()
        self._executor = executor
        self.supervisor = DataUnderstandingSupervisor(
            schema_agent=None,
            quality_agent=None,
            validation_agent=None,
        )
        # Inject dependencies after initialization
        from app.cognitive_data_layer.agents.understanding import (
            DataQualityAgent,
            MappingValidationAgent,
            SchemaAnalysisAgent,
        )

        self.supervisor.schema_agent = SchemaAnalysisAgent(self.schema_discoverer)
        self.supervisor.quality_agent = DataQualityAgent(self.quality_engine)
        self.supervisor.validation_agent = MappingValidationAgent(self.confidence_engine)

    def _run_sync(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Offload a synchronous, CPU-bound call to the default thread pool."""
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(self._executor, fn, *args, **kwargs)

    async def process(
        self,
        source: str | Path | bytes,
        company_id: str | None = None,
        options: dict | None = None,
        hint: str | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        parsed = await parse_source(source, options=options, hint=hint)
        sheets = parsed.raw_data.get("sheets", [])

        # Convert to canonical model (CPU-bound, offloaded to thread pool)
        source_name = str(source) if isinstance(source, (str, Path)) else "binary"
        canonical = await self._run_sync(
            self.canonical_builder.build, source_name, parsed.format, sheets
        )

        # Apply learning system mappings
        if company_id:
            self._apply_learned_mappings(company_id, canonical)

        # Run data quality engine (CPU-bound pandas analysis)
        quality_tasks = []
        for sheet in canonical.sheets:
            for table in sheet.tables:
                df = pd.DataFrame([r.values for r in table.rows])
                quality_tasks.append(
                    self._run_sync(self.quality_engine.analyze, table.name, df, table.columns)
                )
        quality_results = await asyncio.gather(*quality_tasks)
        for issues in quality_results:
            canonical.quality_issues.extend(issues)

        # Run multi-agent understanding
        agent_state = await self.supervisor.arun(sheets)

        # Build knowledge graph (CPU-bound graph construction)
        graph = await self._run_sync(self.knowledge_graph.build_graph, canonical)

        # Assess confidence (CPU-bound)
        confidence_tasks = [
            self._run_sync(self.confidence_engine.batch_assess, table.columns)
            for sheet in canonical.sheets
            for table in sheet.tables
        ]
        confidence_assessments = {}
        for batch in await asyncio.gather(*confidence_tasks):
            confidence_assessments.update(batch)

        # Learn from this run
        if company_id:
            self._learn_from_canonical(company_id, canonical)

        return {
            "canonical": canonical,
            "format": parsed.format,
            "warnings": parsed.warnings,
            "agent_insights": agent_state.insights,
            "quality_report": self.quality_engine.generate_report(canonical.quality_issues),
            "confidence_report": {
                "assessments": {
                    k: {
                        "score": v.score,
                        "explanation": v.explanation,
                        "needs_clarification": v.needs_clarification,
                    }
                    for k, v in confidence_assessments.items()
                },
                "low_confidence": agent_state.confidence_report.get("low_confidence_mappings", []),
            },
            "knowledge_graph": graph,
            "metadata": parsed.metadata,
        }

    def _apply_learned_mappings(self, company_id: str, canonical: CanonicalDataset) -> None:
        for sheet in canonical.sheets:
            for table in sheet.tables:
                for col in table.columns:
                    learned = self.learning_system.get_mapping(company_id, col.name)
                    if learned:
                        from app.cognitive_data_layer.canonical.model import EntityType

                        col.entity_type = EntityType(learned["entity_type"])
                        col.confidence = learned["confidence"]

    def _learn_from_canonical(self, company_id: str, canonical: CanonicalDataset) -> None:
        for sheet in canonical.sheets:
            for table in sheet.tables:
                for col in table.columns:
                    if col.entity_type:
                        self.learning_system.learn_mapping(
                            company_id, col.name, col.entity_type, col.confidence
                        )


async def process_data(
    source: str | Path | bytes,
    company_id: str | None = None,
    options: dict | None = None,
    hint: str | None = None,
) -> dict[str, Any]:
    pipeline = CognitiveDataPipeline()
    return await pipeline.process(source, company_id=company_id, options=options, hint=hint)
