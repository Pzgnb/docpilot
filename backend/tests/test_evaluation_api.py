from pathlib import Path

from app.db.models import Document, DocumentChunk, KnowledgeBase
from app.services.providers import VectorHit
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider


def test_create_list_and_delete_evaluation_case(client):
    knowledge_base = client.post(
        "/api/knowledge-bases", json={"name": "评测知识库", "description": ""}
    ).json()
    payload = {
        "knowledge_base_id": knowledge_base["id"],
        "question": "退款多久？",
        "expected_decision": "answer",
        "expected_file_name": "退款规则.txt",
        "required_keywords": ["30天"],
        "expected_top_rank": 3,
        "expected_citation_ids": [],
    }

    created = client.post("/api/evaluations/cases", json=payload)
    listed = client.get(
        f"/api/evaluations/cases?knowledge_base_id={knowledge_base['id']}"
    )

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json() == [created.json()]
    assert client.delete(f"/api/evaluations/cases/{created.json()['id']}").status_code == 204


def test_batch_run_returns_pass_rate_and_results(client):
    with client.app.state.database.session_factory() as session:
        knowledge_base = KnowledgeBase(name="批量评测", description="")
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
            id="00000000-0000-0000-0000-000000000030",
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

    client.post(
        "/api/evaluations/cases",
        json={
            "knowledge_base_id": knowledge_base_id,
            "question": "退款多久？",
            "expected_decision": "answer",
            "expected_file_name": "退款规则.txt",
            "required_keywords": ["30天"],
            "expected_top_rank": 3,
            "expected_citation_ids": [chunk.id],
        },
    )

    class Store:
        def search(self, knowledge_base_id: str, vector: list[float], limit: int):
            return [VectorHit(chunk.id, document.id, 0, chunk.content, 0.9)]

    client.app.state.embedding_provider = FakeEmbeddingProvider()
    client.app.state.chat_provider = FakeChatProvider([chunk.id])
    client.app.state.vector_store = Store()
    client.app.state.rerank_provider = None

    response = client.post(
        "/api/evaluations/run",
        json={"knowledge_base_id": knowledge_base_id},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["passed"] == 1
    assert response.json()["pass_rate"] == 1.0
    assert response.json()["results"][0]["error_type"] == "none"
