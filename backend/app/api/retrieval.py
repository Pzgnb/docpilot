from fastapi import APIRouter, HTTPException, Request, status

from app.db.base import SessionDependency
from app.schemas.retrieval import RetrievalDebugRequest, RetrievalTraceRead
from app.services.retrieval import HybridRetriever, RetrievalConfig


router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/debug", response_model=RetrievalTraceRead)
def debug_retrieval(
    payload: RetrievalDebugRequest,
    request: Request,
    session: SessionDependency,
):
    if request.app.state.embedding_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_NOT_CONFIGURED", "message": "Embedding模型未配置"},
        )
    retriever = HybridRetriever(
        session=session,
        embedder=request.app.state.embedding_provider,
        vector_store=request.app.state.vector_store,
        reranker=request.app.state.rerank_provider,
    )
    return retriever.retrieve(
        payload.query,
        str(payload.knowledge_base_id),
        RetrievalConfig(
            top_k=payload.top_k,
            vector_weight=payload.vector_weight,
            keyword_weight=payload.keyword_weight,
        ),
    )
