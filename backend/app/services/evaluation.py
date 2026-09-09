from dataclasses import dataclass
from typing import Literal

from app.schemas.chat import ChatResponse
from app.services.retrieval import RetrievalTrace


ErrorType = Literal[
    "none",
    "not_retrieved",
    "ranked_too_low",
    "answer_omission",
    "wrong_citation",
    "wrong_refusal",
]


@dataclass(frozen=True)
class EvaluationCase:
    question: str
    expected_decision: Literal["answer", "insufficient_context"]
    expected_file_name: str | None
    required_keywords: list[str]
    expected_top_rank: int
    expected_citation_ids: list[str]
    id: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str | None
    passed: bool
    error_type: ErrorType
    message: str
    retrieval_trace_id: str


def result(
    case: EvaluationCase,
    response: ChatResponse,
    error_type: ErrorType,
    message: str,
) -> EvaluationResult:
    return EvaluationResult(
        case_id=case.id,
        passed=error_type == "none",
        error_type=error_type,
        message=message,
        retrieval_trace_id=str(response.retrieval_trace_id),
    )


def evaluate_case(
    case: EvaluationCase,
    response: ChatResponse,
    trace: RetrievalTrace,
) -> EvaluationResult:
    if response.decision != case.expected_decision:
        return result(case, response, "wrong_refusal", "回答与预期拒答决策不一致")
    if case.expected_decision == "insufficient_context":
        return result(case, response, "none", "拒答符合预期")

    expected_hits = [
        hit for hit in trace.hits if hit.file_name == case.expected_file_name
    ]
    if not expected_hits:
        return result(case, response, "not_retrieved", "未召回预期文档")
    if min(hit.final_rank for hit in expected_hits) > case.expected_top_rank:
        return result(case, response, "ranked_too_low", "预期文档排序过低")
    missing_keywords = [
        keyword for keyword in case.required_keywords if keyword not in response.answer
    ]
    if missing_keywords:
        return result(
            case,
            response,
            "answer_omission",
            f"回答缺少关键词：{', '.join(missing_keywords)}",
        )

    if case.expected_citation_ids:
        allowed_ids = set(case.expected_citation_ids)
        citations_valid = bool(response.citations) and all(
            citation.chunk_id in allowed_ids for citation in response.citations
        )
    else:
        citations_valid = bool(response.citations) and all(
            citation.file_name == case.expected_file_name
            for citation in response.citations
        )
    if not citations_valid:
        return result(case, response, "wrong_citation", "引用不属于预期证据")
    return result(case, response, "none", "回答通过")
