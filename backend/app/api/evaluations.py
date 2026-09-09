from dataclasses import asdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.db.base import SessionDependency
from app.db.models import (
    EvaluationCaseRecord,
    EvaluationRunRecord,
    KnowledgeBase,
    RetrievalTraceRecord,
)
from app.schemas.chat import ChatResponse, CitationRead
from app.schemas.evaluation import (
    EvaluationCaseCreate,
    EvaluationCaseRead,
    EvaluationRunRead,
    EvaluationRunRequest,
)
from app.services.answering import AnsweringService
from app.services.evaluation import EvaluationCase, evaluate_case
from app.services.retrieval import HybridRetriever, RetrievalConfig


router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.post(
    "/cases",
    response_model=EvaluationCaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    payload: EvaluationCaseCreate, session: SessionDependency
) -> EvaluationCaseRecord:
    if session.get(KnowledgeBase, str(payload.knowledge_base_id)) is None:
        raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_BASE_NOT_FOUND"})
    case = EvaluationCaseRecord(
        knowledge_base_id=str(payload.knowledge_base_id),
        question=payload.question,
        expected_decision=payload.expected_decision,
        expected_file_name=payload.expected_file_name,
        required_keywords=payload.required_keywords,
        expected_top_rank=payload.expected_top_rank,
        expected_citation_ids=payload.expected_citation_ids,
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


@router.get("/cases", response_model=list[EvaluationCaseRead])
def list_cases(
    knowledge_base_id: UUID, session: SessionDependency
) -> list[EvaluationCaseRecord]:
    return list(
        session.scalars(
            select(EvaluationCaseRecord)
            .where(EvaluationCaseRecord.knowledge_base_id == str(knowledge_base_id))
            .order_by(EvaluationCaseRecord.created_at)
        )
    )


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: UUID, session: SessionDependency) -> Response:
    case = session.get(EvaluationCaseRecord, str(case_id))
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "EVALUATION_CASE_NOT_FOUND"})
    session.delete(case)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/run", response_model=EvaluationRunRead)
def run_evaluation(
    payload: EvaluationRunRequest,
    request: Request,
    session: SessionDependency,
) -> EvaluationRunRecord:
    if request.app.state.embedding_provider is None or request.app.state.chat_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_NOT_CONFIGURED"},
        )
    rows = list(
        session.scalars(
            select(EvaluationCaseRecord)
            .where(
                EvaluationCaseRecord.knowledge_base_id
                == str(payload.knowledge_base_id)
            )
            .order_by(EvaluationCaseRecord.created_at)
        )
    )
    results: list[dict] = []
    for row in rows:
        trace = HybridRetriever(
            session,
            request.app.state.embedding_provider,
            request.app.state.vector_store,
            request.app.state.rerank_provider,
        ).retrieve(
            row.question,
            row.knowledge_base_id,
            RetrievalConfig(top_k=payload.top_k),
        )
        answer = AnsweringService(request.app.state.chat_provider).answer(
            row.question, trace.hits, payload.threshold
        )
        trace_record = RetrievalTraceRecord(
            knowledge_base_id=row.knowledge_base_id,
            query=row.question,
            rerank_status=trace.rerank_status,
            hits=[asdict(hit) for hit in trace.hits],
        )
        session.add(trace_record)
        session.flush()
        chat_response = ChatResponse(
            answer=answer.answer,
            decision=answer.decision,
            citations=[CitationRead(**asdict(citation)) for citation in answer.citations],
            retrieval_trace_id=trace_record.id,
            created_at=datetime.now(timezone.utc),
        )
        case = EvaluationCase(
            question=row.question,
            expected_decision=row.expected_decision,
            expected_file_name=row.expected_file_name,
            required_keywords=row.required_keywords,
            expected_top_rank=row.expected_top_rank,
            expected_citation_ids=row.expected_citation_ids,
            id=row.id,
        )
        results.append(asdict(evaluate_case(case, chat_response, trace)))

    passed = sum(item["passed"] for item in results)
    total = len(results)
    run = EvaluationRunRecord(
        knowledge_base_id=str(payload.knowledge_base_id),
        total=total,
        passed=passed,
        pass_rate=passed / total if total else 0.0,
        results=results,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
