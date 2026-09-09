from pathlib import Path

from app.db.models import Document, DocumentChunk, KnowledgeBase
from app.services.providers import VectorHit
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider


def test_chat_returns_verified_citation_and_persists_trace(client):
    with client.app.state.database.session_factory() as session:
        knowledge_base = KnowledgeBase(name="客服资料", description="")
        session.add(knowledge_base)
        session.flush()
        document = Document(
            knowledge_base_id=knowledge_base.id,
            filename="退款规则.txt",
            media_type="text/plain",
            file_path=str(Path("refund.txt")),
            status="ready",
        )
        session.add(document)
        session.flush()
        chunk = DocumentChunk(
            id="00000000-0000-0000-0000-000000000020",
            knowledge_base_id=knowledge_base.id,
            document_id=document.id,
            position=0,
            content="退款期限为30天。",
            char_start=0,
            char_end=9,
        )
        session.add(chunk)
        session.commit()
        knowledge_base_id = knowledge_base.id

    class Store:
        def search(self, knowledge_base_id: str, vector: list[float], limit: int):
            return [VectorHit(chunk.id, document.id, 0, chunk.content, 0.9)]

    client.app.state.embedding_provider = FakeEmbeddingProvider()
    client.app.state.chat_provider = FakeChatProvider([chunk.id])
    client.app.state.vector_store = Store()
    client.app.state.rerank_provider = None

    response = client.post(
        "/api/chat",
        json={
            "knowledge_base_id": knowledge_base_id,
            "question": "退款期限多久？",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "answer"
    assert payload["citations"][0]["chunk_id"] == chunk.id
    assert payload["retrieval_trace_id"]


def test_chat_refuses_when_retrieval_has_no_evidence(client):
    knowledge_base = client.post(
        "/api/knowledge-bases",
        json={"name": "空知识库", "description": ""},
    ).json()

    class EmptyStore:
        def search(self, knowledge_base_id: str, vector: list[float], limit: int):
            return []

    fake_chat = FakeChatProvider()
    client.app.state.embedding_provider = FakeEmbeddingProvider()
    client.app.state.chat_provider = fake_chat
    client.app.state.vector_store = EmptyStore()
    client.app.state.rerank_provider = None

    response = client.post(
        "/api/chat",
        json={
            "knowledge_base_id": knowledge_base["id"],
            "question": "公司年假有几天？",
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "insufficient_context"
    assert fake_chat.calls == 0
