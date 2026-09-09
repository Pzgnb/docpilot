from pathlib import Path

import pytest

from app.db.models import Document, DocumentChunk, KnowledgeBase
from app.services.bailian import BailianRerankProvider
from app.services.providers import VectorHit
from app.services.retrieval import HybridRetriever, RetrievalConfig
from tests.fakes import FakeEmbeddingProvider


class RetrievalStore:
    def __init__(self, hits: list[VectorHit]) -> None:
        self.hits = hits

    def search(self, knowledge_base_id: str, vector: list[float], limit: int):
        return self.hits[:limit]


class ReverseReranker:
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        return [float(index) for index, _ in enumerate(documents)]


@pytest.fixture
def retrieval_rows(client, tmp_path: Path):
    with client.app.state.database.session_factory() as session:
        kb_1 = KnowledgeBase(name="售后知识库", description="")
        kb_2 = KnowledgeBase(name="内部知识库", description="")
        session.add_all([kb_1, kb_2])
        session.flush()
        doc_1 = Document(
            knowledge_base_id=kb_1.id,
            filename="退款规则.txt",
            media_type="text/plain",
            file_path=str(tmp_path / "refund.txt"),
            status="ready",
        )
        doc_2 = Document(
            knowledge_base_id=kb_1.id,
            filename="物流规则.txt",
            media_type="text/plain",
            file_path=str(tmp_path / "shipping.txt"),
            status="ready",
        )
        other_doc = Document(
            knowledge_base_id=kb_2.id,
            filename="内部制度.txt",
            media_type="text/plain",
            file_path=str(tmp_path / "internal.txt"),
            status="ready",
        )
        session.add_all([doc_1, doc_2, other_doc])
        session.flush()
        chunks = [
            DocumentChunk(
                id="00000000-0000-0000-0000-000000000001",
                knowledge_base_id=kb_1.id,
                document_id=doc_1.id,
                position=0,
                content="退款期限为30天，超过期限无法恢复。",
                char_start=0,
                char_end=19,
            ),
            DocumentChunk(
                id="00000000-0000-0000-0000-000000000002",
                knowledge_base_id=kb_1.id,
                document_id=doc_2.id,
                position=0,
                content="标准物流通常需要三到五天。",
                char_start=0,
                char_end=14,
            ),
            DocumentChunk(
                id="00000000-0000-0000-0000-000000000003",
                knowledge_base_id=kb_2.id,
                document_id=other_doc.id,
                position=0,
                content="内部制度不得对外公开。",
                char_start=0,
                char_end=12,
            ),
        ]
        session.add_all(chunks)
        session.commit()
        yield session, kb_1, chunks


def test_hybrid_retrieval_exposes_rank_change(retrieval_rows):
    session, knowledge_base, chunks = retrieval_rows
    store = RetrievalStore(
        [
            VectorHit(chunks[0].id, chunks[0].document_id, 0, chunks[0].content, 0.9),
            VectorHit(chunks[1].id, chunks[1].document_id, 0, chunks[1].content, 0.8),
        ]
    )
    retriever = HybridRetriever(
        session, FakeEmbeddingProvider(), store, ReverseReranker()
    )

    trace = retriever.retrieve("退款多久", knowledge_base.id, RetrievalConfig(top_k=2))

    assert all(hit.initial_rank >= 1 for hit in trace.hits)
    assert all(hit.final_rank >= 1 for hit in trace.hits)
    assert trace.hits == sorted(trace.hits, key=lambda hit: hit.final_rank)
    assert trace.rerank_status == "applied"
    assert trace.hits[0].initial_rank != trace.hits[0].final_rank


def test_retrieval_never_returns_another_knowledge_base(retrieval_rows):
    session, knowledge_base, chunks = retrieval_rows
    store = RetrievalStore(
        [
            VectorHit(chunks[2].id, chunks[2].document_id, 0, chunks[2].content, 1.0),
            VectorHit(chunks[0].id, chunks[0].document_id, 0, chunks[0].content, 0.9),
        ]
    )
    retriever = HybridRetriever(session, FakeEmbeddingProvider(), store)

    trace = retriever.retrieve("内部制度", knowledge_base.id, RetrievalConfig(top_k=5))

    assert {hit.knowledge_base_id for hit in trace.hits} == {knowledge_base.id}
    assert trace.rerank_status == "not_configured"


@pytest.mark.parametrize(
    ("vector_weight", "keyword_weight"),
    [(1.1, -0.1), (0.5, 0.4)],
)
def test_retrieval_weights_must_be_valid(vector_weight: float, keyword_weight: float):
    with pytest.raises(ValueError):
        RetrievalConfig(
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
        )


def test_bailian_reranker_restores_scores_to_input_order():
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "results": [
                    {"index": 1, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.2},
                ]
            }

    class Client:
        def post(self, url: str, *, headers: dict, json: dict):
            assert url.endswith("/compatible-api/v1/reranks")
            assert json["top_n"] == 2
            return Response()

    provider = BailianRerankProvider(
        api_key="test-key",
        workspace_id="test-workspace",
        model="qwen3-rerank",
        client=Client(),
    )

    assert provider.rerank("query", ["first", "second"]) == [0.2, 0.9]
