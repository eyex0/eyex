from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=100_000)
    thread_id: str | None = Field(None, max_length=256)
    config: dict | None = None


class AgentStep(BaseModel):
    node: str
    output: str
    duration_ms: int


class WorkflowResult(BaseModel):
    success: bool
    output: str
    steps: list[AgentStep] = []
    thread_id: str | None = None
    error: str | None = None


class AgentResponse(BaseModel):
    result: WorkflowResult
