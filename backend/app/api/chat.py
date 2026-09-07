from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, status

from app.db.base import SessionDependency
from app.db.models import ChatRecord, KnowledgeBase, RetrievalTraceRecord
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.answering import AnsweringService
from app.services.retrieval import HybridRetriever, RetrievalConfig


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    session: SessionDependency,
) -> ChatRecord:
    if session.get(KnowledgeBase, str(payload.knowledge_base_id)) is None:
        raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_BASE_NOT_FOUND"})
    if request.app.state.embedding_provider is None or request.app.state.chat_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_NOT_CONFIGURED", "message": "模型未配置"},
        )

    trace = HybridRetriever(
        session=session,
        embedder=request.app.state.embedding_provider,
        vector_store=request.app.state.vector_store,
        reranker=request.app.state.rerank_provider,
    ).retrieve(
        payload.question,
        str(payload.knowledge_base_id),
        RetrievalConfig(top_k=payload.top_k),
    )
    result = AnsweringService(request.app.state.chat_provider).answer(
        payload.question,
        trace.hits,
        payload.threshold,
    )

    trace_record = RetrievalTraceRecord(
        knowledge_base_id=str(payload.knowledge_base_id),
        query=payload.question,
        rerank_status=trace.rerank_status,
        hits=[asdict(hit) for hit in trace.hits],
    )
    session.add(trace_record)
    session.flush()
    chat_record = ChatRecord(
        knowledge_base_id=str(payload.knowledge_base_id),
        retrieval_trace_id=trace_record.id,
        question=payload.question,
        answer=result.answer,
        decision=result.decision,
        citations=[asdict(citation) for citation in result.citations],
    )
    session.add(chat_record)
    session.commit()
    session.refresh(chat_record)
    return chat_record
