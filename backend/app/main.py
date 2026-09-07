from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.knowledge_bases import router as knowledge_bases_router
from app.api.retrieval import router as retrieval_router
from app.core.config import Settings, get_settings
from app.db.base import Base, Database
from app.services.bailian import (
    BailianChatProvider,
    BailianEmbeddingProvider,
    BailianRerankProvider,
)
from app.services.vector_store import QdrantVectorStore


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = Database(resolved_settings.database_url)
        application.state.database = database
        Base.metadata.create_all(database.engine)
        try:
            yield
        finally:
            database.engine.dispose()

    application = FastAPI(title="DocPilot API", version="0.1.0", lifespan=lifespan)
    application.state.settings = resolved_settings
    application.state.embedding_provider = (
        BailianEmbeddingProvider(
            api_key=resolved_settings.bailian_api_key,
            base_url=resolved_settings.bailian_base_url,
            model=resolved_settings.embedding_model,
        )
        if resolved_settings.model_configured
        else None
    )
    application.state.chat_provider = (
        BailianChatProvider(
            api_key=resolved_settings.bailian_api_key or "",
            base_url=resolved_settings.bailian_base_url,
            model=resolved_settings.chat_model,
        )
        if resolved_settings.model_configured
        else None
    )
    application.state.vector_store = QdrantVectorStore(resolved_settings.qdrant_url)
    application.state.rerank_provider = (
        BailianRerankProvider(
            api_key=resolved_settings.bailian_api_key or "",
            workspace_id=resolved_settings.bailian_workspace_id or "",
            model=resolved_settings.rerank_model,
        )
        if resolved_settings.model_configured
        and resolved_settings.bailian_workspace_id
        else None
    )
    application.include_router(health_router)
    application.include_router(knowledge_bases_router)
    application.include_router(documents_router)
    application.include_router(retrieval_router)
    application.include_router(chat_router)
    return application


app = create_app()
