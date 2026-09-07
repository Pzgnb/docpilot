import math
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RetrievalDebugRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    knowledge_base_id: UUID
    top_k: int = Field(default=5, ge=1, le=50)
    vector_weight: float = Field(default=0.65, ge=0, le=1)
    keyword_weight: float = Field(default=0.35, ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "RetrievalDebugRequest":
        if not math.isclose(self.vector_weight + self.keyword_weight, 1.0):
            raise ValueError("retrieval weights must sum to one")
        return self


class RetrievalHitRead(BaseModel):
    chunk_id: str
    knowledge_base_id: str
    document_id: str
    file_name: str
    content: str
    vector_score: float
    keyword_score: float
    fusion_score: float
    rerank_score: float | None
    initial_rank: int
    final_rank: int


class RetrievalTraceRead(BaseModel):
    query: str
    knowledge_base_id: str
    rerank_status: Literal["not_configured", "applied"]
    hits: list[RetrievalHitRead]
