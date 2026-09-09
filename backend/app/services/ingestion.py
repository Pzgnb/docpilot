from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.services.chunking import chunk_text
from app.services.parsing import parse_document
from app.services.providers import (
    EmbeddedChunk,
    EmbeddingError,
    EmbeddingProvider,
    VectorStore,
)


def ingest_document(
    session: Session,
    document_id: str,
    embedder: EmbeddingProvider,
    vector_store: VectorStore,
) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise LookupError("Document not found")

    document.status = "processing"
    document.error_code = None
    document.error_message = None
    session.commit()

    try:
        vector_store.delete_document(document.id)
        session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        parsed = parse_document(Path(document.file_path), document.media_type)
        chunks = chunk_text(parsed.text, document.id)
        vectors = embedder.embed([chunk.content for chunk in chunks])
        if len(vectors) != len(chunks):
            raise EmbeddingError("Embedding provider returned an unexpected vector count")

        embedded_chunks = [
            EmbeddedChunk(
                id=chunk.id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                position=chunk.position,
                content=chunk.content,
                vector=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        session.add_all(
            DocumentChunk(
                id=chunk.id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                position=chunk.position,
                content=chunk.content,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
            for chunk in chunks
        )
        session.flush()
        vector_store.upsert(embedded_chunks)
        document.status = "ready"
        document.chunk_count = len(chunks)
        session.commit()
        session.refresh(document)
        return document
    except Exception as exc:
        session.rollback()
        failed_document = session.get(Document, document_id)
        if failed_document is not None:
            failed_document.status = "failed"
            failed_document.chunk_count = 0
            failed_document.error_code = (
                "EMBEDDING_FAILED"
                if isinstance(exc, EmbeddingError)
                else "DOCUMENT_PROCESSING_FAILED"
            )
            failed_document.error_message = str(exc)
            session.commit()
        raise
