from pydantic import BaseModel, Field


class MemoryStoreRequest(BaseModel):
    key: str = Field(..., max_length=512)
    value: str = Field(..., max_length=100_000)
    memory_type: str = Field(default="fact", max_length=50)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class LongTermMemoryEntry(BaseModel):
    key: str = Field(..., max_length=512)
    value: str = Field(..., max_length=100_000)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    updated_at: str | None = Field(None, max_length=100)


class MemorySummary(BaseModel):
    session_id: str
    message_count: int
    long_term: dict[str, str]
    agent_memories: dict[str, dict[str, str]]


class MemoryDeleteResult(BaseModel):
    deleted: dict[str, int]


class MemoryOperationResult(BaseModel):
    success: bool
