from app.services.providers import EmbeddedChunk, VectorHit


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index), float(len(text))] for index, text in enumerate(texts)]


class FailingEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        from app.services.providers import EmbeddingError

        raise EmbeddingError("fake provider failure")


class FakeVectorStore:
    def __init__(self) -> None:
        self.rows: list[EmbeddedChunk] = []
        self.deleted_document_ids: list[str] = []

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        self.rows.extend(chunks)

    def delete_document(self, document_id: str) -> None:
        self.deleted_document_ids.append(document_id)
        self.rows = [row for row in self.rows if row.document_id != document_id]

    def search(
        self, knowledge_base_id: str, vector: list[float], limit: int
    ) -> list[VectorHit]:
        return []
