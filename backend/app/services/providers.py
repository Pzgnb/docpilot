from dataclasses import dataclass
from typing import Protocol


class EmbeddingError(RuntimeError):
    pass


class RerankError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddedChunk:
    id: str
    knowledge_base_id: str
    document_id: str
    position: int
    content: str
    vector: list[float]


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    document_id: str
    position: int
    content: str
    score: float


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class RerankProvider(Protocol):
    def rerank(self, query: str, documents: list[str]) -> list[float]: ...


class VectorStore(Protocol):
    def upsert(self, chunks: list[EmbeddedChunk]) -> None: ...

    def delete_document(self, document_id: str) -> None: ...

    def search(
        self, knowledge_base_id: str, vector: list[float], limit: int
    ) -> list[VectorHit]: ...
