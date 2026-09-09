from app.services.answering import AnsweringService
from app.services.retrieval import RetrievalHit
from tests.fakes import FakeChatProvider


def known_hits() -> list[RetrievalHit]:
    return [
        RetrievalHit(
            chunk_id="chunk-1",
            knowledge_base_id="kb-1",
            document_id="doc-1",
            file_name="退款规则.txt",
            content="退款期限为30天。",
            vector_score=0.9,
            keyword_score=1.0,
            fusion_score=0.9,
            rerank_score=None,
            initial_rank=1,
            final_rank=1,
        )
    ]


def test_low_score_refuses_without_calling_chat():
    fake_chat = FakeChatProvider()
    service = AnsweringService(fake_chat)

    result = service.answer("文档外的问题", hits=[], threshold=0.55)

    assert result.decision == "insufficient_context"
    assert result.citations == []
    assert fake_chat.calls == 0
    assert result.answer == "知识库中没有足够信息回答这个问题。"


def test_answer_citations_are_limited_to_supplied_chunks():
    service = AnsweringService(FakeChatProvider(["chunk-1", "made-up-chunk"]))
    hits = known_hits()

    result = service.answer("退款多久", hits=hits, threshold=0.55)

    assert result.decision == "answer"
    assert {citation.chunk_id for citation in result.citations} <= {
        hit.chunk_id for hit in hits
    }
    assert {citation.chunk_id for citation in result.citations} == {"chunk-1"}


def test_answer_without_a_valid_citation_becomes_refusal():
    service = AnsweringService(FakeChatProvider(["made-up-chunk"]))

    result = service.answer("退款多久", hits=known_hits(), threshold=0.55)

    assert result.decision == "insufficient_context"
    assert result.citations == []
