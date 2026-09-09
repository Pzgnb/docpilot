from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    knowledge_base_id: UUID
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.55, ge=0, le=1)


class CitationRead(BaseModel):
    chunk_id: str
    document_id: str
    file_name: str
    content: str


class ChatResponse(BaseModel):
    answer: str
    decision: Literal["answer", "insufficient_context"]
    citations: list[CitationRead]
    retrieval_trace_id: UUID
    created_at: datetime
