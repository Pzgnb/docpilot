from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select

from app.db.base import SessionDependency
from app.db.models import Document, KnowledgeBase
from app.schemas.document import DocumentRead
from app.services.ingestion import ingest_document


router = APIRouter(tags=["documents"])
SUPPORTED_MEDIA_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def document_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "DOCUMENT_NOT_FOUND", "message": "文档不存在"},
    )


@router.post(
    "/api/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    knowledge_base_id: UUID,
    file: UploadFile,
    request: Request,
    session: SessionDependency,
) -> Document:
    knowledge_base = session.get(KnowledgeBase, str(knowledge_base_id))
    if knowledge_base is None:
        raise HTTPException(status_code=404, detail={"code": "KNOWLEDGE_BASE_NOT_FOUND"})
    if file.content_type not in SUPPORTED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "UNSUPPORTED_DOCUMENT", "message": "不支持该文档格式"},
        )

    filename = Path(file.filename or "document").name
    storage_dir: Path = request.app.state.settings.storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_path = storage_dir / f"{uuid4()}{Path(filename).suffix.lower()}"
    stored_path.write_bytes(file.file.read())

    document = Document(
        knowledge_base_id=knowledge_base.id,
        filename=filename,
        media_type=file.content_type,
        file_path=str(stored_path),
    )
    knowledge_base.document_count += 1
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.get(
    "/api/knowledge-bases/{knowledge_base_id}/documents",
    response_model=list[DocumentRead],
)
def list_documents(
    knowledge_base_id: UUID, session: SessionDependency
) -> list[Document]:
    statement = (
        select(Document)
        .where(Document.knowledge_base_id == str(knowledge_base_id))
        .order_by(Document.created_at)
    )
    return list(session.scalars(statement))


def process_existing_document(
    document_id: UUID, request: Request, session: SessionDependency
) -> Document:
    document = session.get(Document, str(document_id))
    if document is None:
        raise document_not_found()
    embedder = request.app.state.embedding_provider
    if embedder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_NOT_CONFIGURED", "message": "Embedding模型未配置"},
        )
    try:
        return ingest_document(session, document.id, embedder, request.app.state.vector_store)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "DOCUMENT_PROCESSING_FAILED", "message": str(exc)},
        ) from exc


@router.post("/api/documents/{document_id}/process", response_model=DocumentRead)
def process_document(
    document_id: UUID, request: Request, session: SessionDependency
) -> Document:
    return process_existing_document(document_id, request, session)


@router.post("/api/documents/{document_id}/retry", response_model=DocumentRead)
def retry_document(
    document_id: UUID, request: Request, session: SessionDependency
) -> Document:
    return process_existing_document(document_id, request, session)


@router.delete("/api/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID, request: Request, session: SessionDependency
) -> Response:
    document = session.get(Document, str(document_id))
    if document is None:
        raise document_not_found()
    request.app.state.vector_store.delete_document(document.id)
    path = Path(document.file_path)
    if path.exists():
        path.unlink()
    knowledge_base = session.get(KnowledgeBase, document.knowledge_base_id)
    if knowledge_base is not None:
        knowledge_base.document_count = max(knowledge_base.document_count - 1, 0)
    session.delete(document)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
