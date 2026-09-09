import math
import re
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.services.providers import EmbeddingProvider, RerankProvider, VectorStore


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 5
    vector_weight: float = 0.65
    keyword_weight: float = 0.35

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if not 0 <= self.vector_weight <= 1 or not 0 <= self.keyword_weight <= 1:
            raise ValueError("retrieval weights must be between zero and one")
        if not math.isclose(self.vector_weight + self.keyword_weight, 1.0):
            raise ValueError("retrieval weights must sum to one")


@dataclass
class RetrievalHit:
    chunk_id: str
    knowledge_base_id: str
    document_id: str
    file_name: str
    content: str
    vector_score: float
    keyword_score: float
    fusion_score: float
    rerank_score: float | None
    initial_rank: int
    final_rank: int


@dataclass(frozen=True)
class RetrievalTrace:
    query: str
    knowledge_base_id: str
    rerank_status: str
    hits: list[RetrievalHit]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text.lower())


def bm25_scores(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    tokenized = [tokenize(document) for document in documents]
    query_tokens = tokenize(query)
    average_length = sum(len(tokens) for tokens in tokenized) / len(tokenized) or 1
    document_frequency = Counter(
        token for tokens in tokenized for token in set(tokens)
    )
    scores: list[float] = []
    for tokens in tokenized:
        frequencies = Counter(tokens)
        score = 0.0
        for token in query_tokens:
            frequency = frequencies[token]
            if frequency == 0:
                continue
            df = document_frequency[token]
            inverse_frequency = math.log(
                1 + (len(documents) - df + 0.5) / (df + 0.5)
            )
            denominator = frequency + 1.5 * (
                1 - 0.75 + 0.75 * len(tokens) / average_length
            )
            score += inverse_frequency * frequency * 2.5 / denominator
        scores.append(score)
    return scores


def normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    maximum = max(scores.values())
    minimum = min(scores.values())
    if math.isclose(maximum, minimum):
        value = 1.0 if maximum > 0 else 0.0
        return {key: value for key in scores}
    return {key: (value - minimum) / (maximum - minimum) for key, value in scores.items()}


class HybridRetriever:
    def __init__(
        self,
        session: Session,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
        reranker: RerankProvider | None = None,
    ) -> None:
        self.session = session
        self.embedder = embedder
        self.vector_store = vector_store
        self.reranker = reranker

    def retrieve(
        self,
        query: str,
        knowledge_base_id: str,
        config: RetrievalConfig,
    ) -> RetrievalTrace:
        rows = list(
            self.session.execute(
                select(DocumentChunk, Document.filename)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(DocumentChunk.knowledge_base_id == knowledge_base_id)
            ).all()
        )
        if not rows:
            return RetrievalTrace(query, knowledge_base_id, "not_configured", [])

        chunks = {chunk.id: (chunk, filename) for chunk, filename in rows}
        candidate_limit = max(config.top_k * 4, 20)
        query_vector = self.embedder.embed([query])[0]
        vector_hits = self.vector_store.search(
            knowledge_base_id, query_vector, candidate_limit
        )
        vector_raw = {
            hit.chunk_id: hit.score for hit in vector_hits if hit.chunk_id in chunks
        }
        keyword_values = bm25_scores(query, [chunk.content for chunk, _ in rows])
        keyword_raw = {
            chunk.id: score
            for (chunk, _), score in zip(rows, keyword_values, strict=True)
            if score > 0
        }
        candidate_ids = set(vector_raw) | set(keyword_raw)
        vector_normalized = normalize(
            {chunk_id: vector_raw.get(chunk_id, 0.0) for chunk_id in candidate_ids}
        )
        keyword_normalized = normalize(
            {chunk_id: keyword_raw.get(chunk_id, 0.0) for chunk_id in candidate_ids}
        )

        hits = []
        for chunk_id in candidate_ids:
            chunk, filename = chunks[chunk_id]
            fusion_score = (
                config.vector_weight * vector_normalized[chunk_id]
                + config.keyword_weight * keyword_normalized[chunk_id]
            )
            hits.append(
                RetrievalHit(
                    chunk_id=chunk.id,
                    knowledge_base_id=chunk.knowledge_base_id,
                    document_id=chunk.document_id,
                    file_name=filename,
                    content=chunk.content,
                    vector_score=vector_raw.get(chunk_id, 0.0),
                    keyword_score=keyword_raw.get(chunk_id, 0.0),
                    fusion_score=fusion_score,
                    rerank_score=None,
                    initial_rank=0,
                    final_rank=0,
                )
            )
        hits.sort(key=lambda hit: (-hit.fusion_score, hit.chunk_id))
        hits = hits[:candidate_limit]
        for rank, hit in enumerate(hits, 1):
            hit.initial_rank = rank

        rerank_status = "not_configured"
        if self.reranker is not None and hits:
            scores = self.reranker.rerank(query, [hit.content for hit in hits])
            if len(scores) != len(hits):
                raise ValueError("reranker returned an unexpected score count")
            for hit, score in zip(hits, scores, strict=True):
                hit.rerank_score = score
            hits.sort(
                key=lambda hit: (
                    -(hit.rerank_score if hit.rerank_score is not None else 0),
                    hit.initial_rank,
                )
            )
            rerank_status = "applied"

        hits = hits[: config.top_k]
        for rank, hit in enumerate(hits, 1):
            hit.final_rank = rank
        return RetrievalTrace(query, knowledge_base_id, rerank_status, hits)
