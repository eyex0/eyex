from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=12_000)
    session_id: str | None = Field(None, max_length=256)
    stream: bool = False


class ChatMessage(BaseModel):
    id: str = Field(..., max_length=256)
    role: str = Field(..., max_length=50)
    content: str = Field(..., max_length=1_000_000)
    agent_name: str | None = Field(None, max_length=100)
    created_at: str | None = Field(None, max_length=100)


class ConversationHistory(BaseModel):
    session_id: str
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    success: bool
    output: str
    steps: list[dict] = []
    session_id: str | None = None
    error: str | None = None
