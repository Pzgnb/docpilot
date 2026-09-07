def test_retrieval_debug_returns_intermediate_scores(client):
    from pathlib import Path

    from app.db.models import Document, DocumentChunk, KnowledgeBase
    from app.services.providers import VectorHit
    from tests.fakes import FakeEmbeddingProvider

    class Store:
        def search(self, knowledge_base_id: str, vector: list[float], limit: int):
            return [VectorHit(chunk.id, document.id, 0, chunk.content, 0.8)]

    with client.app.state.database.session_factory() as session:
        knowledge_base = KnowledgeBase(name="调试知识库", description="")
        session.add(knowledge_base)
        session.flush()
        document = Document(
            knowledge_base_id=knowledge_base.id,
            filename="guide.txt",
            media_type="text/plain",
            file_path=str(Path("guide.txt")),
            status="ready",
        )
        session.add(document)
        session.flush()
        chunk = DocumentChunk(
            id="00000000-0000-0000-0000-000000000010",
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

    client.app.state.embedding_provider = FakeEmbeddingProvider()
    client.app.state.vector_store = Store()
    client.app.state.rerank_provider = None

    response = client.post(
        "/api/retrieval/debug",
        json={
            "query": "退款多久",
            "knowledge_base_id": knowledge_base_id,
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rerank_status"] == "not_configured"
    assert payload["hits"][0]["file_name"] == "guide.txt"
    assert payload["hits"][0]["vector_score"] == 0.8
    assert "fusion_score" in payload["hits"][0]
