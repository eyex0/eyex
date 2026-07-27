from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from packages.cognitive_kernel import PX_AI

logger = logging.getLogger("pix.agents.analyst")


class AnalystOutput(BaseModel):
    summary: str = Field(description="Executive summary of the analysis")
    metrics_analyzed: list[str] = Field(description="List of metrics that were analyzed")
    key_findings: list[str] = Field(description="Key findings from the data analysis")
    trends: list[dict] = Field(description="Identified trends with direction and magnitude", default=[])
    anomalies: list[dict] = Field(description="Detected anomalies with details", default=[])
    data_quality: str = Field(description="Assessment of data quality and completeness")
    confidence: float = Field(description="Confidence score 0-1", ge=0.0, le=1.0)


class AnalystAgent:
    def __init__(self, ai_control_plane):
        self.ai = ai_control_plane

    async def execute(self, input_text: str, session_id: str | None = None) -> AnalystOutput:
        # This is a simplified call to the AI Control Plane.
        # In a real implementation, we would pass more structured context.
        result = await self.ai.generate(
            task="business_analysis",
            context={"input": input_text},
            goal="Provide a structured analysis of the business data, including summary, metrics analyzed, key findings, trends, anomalies, data quality, and confidence score.",
            budget="medium",
            privacy="enterprise",
        )
        
        # In a real implementation, the AI Control Plane would return a structured object
        # that could be directly used to instantiate AnalystOutput.
        # For now, we'll just return a placeholder.
        return AnalystOutput(
            summary="Analysis summary from AI Control Plane.",
            metrics_analyzed=["revenue", "churn"],
            key_findings=["Revenue is up, but so is churn."],
            trends=[{"metric": "revenue", "direction": "up"}],
            anomalies=[],
            data_quality="good",
            confidence=0.9,
        )

def create_analyst_agent(settings, **kwargs) -> AnalystAgent:
    return AnalystAgent(ai_control_plane=PX_AI)
