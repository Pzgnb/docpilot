from pathlib import Path
from types import SimpleNamespace

import pytest

from app.db.models import Document, KnowledgeBase
from app.services.bailian import BailianEmbeddingProvider
from app.services.ingestion import ingest_document
from app.services.providers import EmbeddingError
from tests.fakes import (
    FakeEmbeddingProvider,
    FakeVectorStore,
    FailingEmbeddingProvider,
)


@pytest.fixture
def uploaded_document(client, tmp_path: Path):
    with client.app.state.database.session_factory() as session:
        knowledge_base = KnowledgeBase(name="内部手册", description="")
        session.add(knowledge_base)
        session.commit()
        session.refresh(knowledge_base)

        path = tmp_path / "guide.txt"
        path.write_text("退款期限为30天。" * 100, encoding="utf-8")
        document = Document(
            knowledge_base_id=knowledge_base.id,
            filename=path.name,
            media_type="text/plain",
            file_path=str(path),
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        yield session, document


def test_ingestion_marks_ready_only_after_vectors_are_written(uploaded_document):
    session, document = uploaded_document
    store = FakeVectorStore()

    ingest_document(session, document.id, FakeEmbeddingProvider(), store)

    session.refresh(document)
    assert document.status == "ready"
    assert document.chunk_count > 0
    assert len(store.rows) == document.chunk_count
    assert all(row.knowledge_base_id == document.knowledge_base_id for row in store.rows)


def test_ingestion_failure_is_retryable(uploaded_document):
    session, document = uploaded_document

    with pytest.raises(EmbeddingError):
        ingest_document(session, document.id, FailingEmbeddingProvider(), FakeVectorStore())

    session.refresh(document)
    assert document.status == "failed"
    assert document.error_code == "EMBEDDING_FAILED"


def test_bailian_embedding_batches_at_most_ten_inputs():
    calls: list[list[str]] = []

    class Embeddings:
        def create(self, *, model: str, input: list[str]):
            calls.append(input)
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[float(text)]) for text in input]
            )

    client = SimpleNamespace(embeddings=Embeddings())
    provider = BailianEmbeddingProvider(client=client, model="text-embedding-v4")

    vectors = provider.embed([str(index) for index in range(23)])

    assert [len(batch) for batch in calls] == [10, 10, 3]
    assert vectors == [[float(index)] for index in range(23)]
