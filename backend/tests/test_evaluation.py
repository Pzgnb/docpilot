from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.chat import ChatResponse, CitationRead
from app.services.evaluation import EvaluationCase, evaluate_case
from app.services.retrieval import RetrievalHit, RetrievalTrace


def response(decision="answer", answer="退款期限为30天。", citation_id="good"):
    citations = []
    if citation_id:
        citations = [
            CitationRead(
                chunk_id=citation_id,
                document_id="doc-1",
                file_name="退款规则.txt",
                content="退款期限为30天。",
            )
        ]
    return ChatResponse(
        answer=answer,
        decision=decision,
        citations=citations,
        retrieval_trace_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )


def hit(file_name="退款规则.txt", final_rank=1):
    return RetrievalHit(
        chunk_id="good",
        knowledge_base_id="kb-1",
        document_id="doc-1",
        file_name=file_name,
        content="退款期限为30天。",
        vector_score=0.9,
        keyword_score=1.0,
        fusion_score=0.9,
        rerank_score=None,
        initial_rank=1,
        final_rank=final_rank,
    )


def trace(hits):
    return RetrievalTrace("退款多久", "kb-1", "not_configured", hits)


@pytest.mark.parametrize(
    ("case", "chat_response", "retrieval_trace", "expected_error"),
    [
        (
            EvaluationCase("退款多久", "answer", "退款规则.txt", ["30天"], 3, []),
            response(),
            trace([]),
            "not_retrieved",
        ),
        (
            EvaluationCase("退款多久", "answer", "退款规则.txt", ["30天"], 3, []),
            response(),
            trace([hit(final_rank=4)]),
            "ranked_too_low",
        ),
        (
            EvaluationCase("退款多久", "answer", "退款规则.txt", ["30天"], 3, []),
            response(answer="请查看退款规则。"),
            trace([hit()]),
            "answer_omission",
        ),
        (
            EvaluationCase(
                "退款多久", "answer", "退款规则.txt", ["30天"], 3, ["good"]
            ),
            response(citation_id="bad"),
            trace([hit()]),
            "wrong_citation",
        ),
        (
            EvaluationCase("退款多久", "answer", "退款规则.txt", ["30天"], 3, []),
            response(decision="insufficient_context", answer="资料不足", citation_id=""),
            trace([hit()]),
            "wrong_refusal",
        ),
    ],
)
def test_error_classification(case, chat_response, retrieval_trace, expected_error):
    assert evaluate_case(case, chat_response, retrieval_trace).error_type == expected_error


def test_valid_evaluation_passes():
    case = EvaluationCase(
        "退款多久", "answer", "退款规则.txt", ["30天"], 3, ["good"]
    )

    result = evaluate_case(case, response(), trace([hit()]))

    assert result.passed is True
    assert result.error_type == "none"
