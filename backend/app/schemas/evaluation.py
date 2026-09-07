from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationCaseCreate(BaseModel):
    knowledge_base_id: UUID
    question: str = Field(min_length=1, max_length=2000)
    expected_decision: Literal["answer", "insufficient_context"]
    expected_file_name: str | None = Field(default=None, max_length=500)
    required_keywords: list[str] = Field(default_factory=list)
    expected_top_rank: int = Field(default=3, ge=1, le=50)
    expected_citation_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def answer_requires_expected_file(self) -> "EvaluationCaseCreate":
        if self.expected_decision == "answer" and not self.expected_file_name:
            raise ValueError("expected_file_name is required for answer cases")
        return self


class EvaluationCaseRead(EvaluationCaseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class EvaluationRunRequest(BaseModel):
    knowledge_base_id: UUID
    threshold: float = Field(default=0.55, ge=0, le=1)
    top_k: int = Field(default=5, ge=1, le=20)


class EvaluationResultRead(BaseModel):
    case_id: str | None
    passed: bool
    error_type: Literal[
        "none",
        "not_retrieved",
        "ranked_too_low",
        "answer_omission",
        "wrong_citation",
        "wrong_refusal",
    ]
    message: str
    retrieval_trace_id: str


class EvaluationRunRead(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    total: int
    passed: int
    pass_rate: float
    results: list[EvaluationResultRead]
    created_at: datetime
