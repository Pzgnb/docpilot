from dataclasses import dataclass
from typing import Literal

from app.services.providers import AnswerContext, ChatProvider
from app.services.retrieval import RetrievalHit


REFUSAL_TEXT = "知识库中没有足够信息回答这个问题。"


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    document_id: str
    file_name: str
    content: str


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    decision: Literal["answer", "insufficient_context"]
    citations: list[Citation]


class AnsweringService:
    def __init__(self, chat_provider: ChatProvider) -> None:
        self.chat_provider = chat_provider

    def answer(
        self,
        question: str,
        hits: list[RetrievalHit],
        threshold: float = 0.55,
    ) -> AnswerResult:
        best_score = max(
            (
                hit.rerank_score
                if hit.rerank_score is not None
                else hit.fusion_score
                for hit in hits
            ),
            default=0.0,
        )
        if best_score < threshold:
            return AnswerResult(REFUSAL_TEXT, "insufficient_context", [])

        contexts = [
            AnswerContext(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                file_name=hit.file_name,
                content=hit.content,
            )
            for hit in hits
        ]
        generated = self.chat_provider.answer(question, contexts)
        allowed = {context.chunk_id: context for context in contexts}
        valid_ids = list(dict.fromkeys(
            citation_id
            for citation_id in generated.citation_ids
            if citation_id in allowed
        ))
        if not generated.answer or not valid_ids:
            return AnswerResult(REFUSAL_TEXT, "insufficient_context", [])
        citations = [
            Citation(
                chunk_id=allowed[citation_id].chunk_id,
                document_id=allowed[citation_id].document_id,
                file_name=allowed[citation_id].file_name,
                content=allowed[citation_id].content,
            )
            for citation_id in valid_ids
        ]
        return AnswerResult(generated.answer, "answer", citations)


def answer_question(
    question: str,
    hits: list[RetrievalHit],
    chat_provider: ChatProvider,
    threshold: float = 0.55,
) -> AnswerResult:
    return AnsweringService(chat_provider).answer(question, hits, threshold)
