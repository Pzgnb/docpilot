from qdrant_client import QdrantClient, models

from app.services.providers import EmbeddedChunk, VectorHit


class QdrantVectorStore:
    def __init__(
        self,
        url: str,
        collection_name: str = "docpilot_chunks",
        vector_size: int = 1024,
    ) -> None:
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=self.url,
                check_compatibility=False,
            )
        return self._client

    def ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size, distance=models.Distance.COSINE
            ),
        )

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        if not chunks:
            return
        self.ensure_collection()
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=chunk.id,
                    vector=chunk.vector,
                    payload={
                        "knowledge_base_id": chunk.knowledge_base_id,
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.id,
                        "position": chunk.position,
                        "content": chunk.content,
                    },
                )
                for chunk in chunks
            ],
        )

    def delete_document(self, document_id: str) -> None:
        if not self.client.collection_exists(self.collection_name):
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id", match=models.MatchValue(value=document_id)
                        )
                    ]
                )
            ),
        )

    def search(
        self, knowledge_base_id: str, vector: list[float], limit: int
    ) -> list[VectorHit]:
        if not self.client.collection_exists(self.collection_name):
            return []
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="knowledge_base_id",
                        match=models.MatchValue(value=knowledge_base_id),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            VectorHit(
                chunk_id=str(point.payload["chunk_id"]),
                document_id=str(point.payload["document_id"]),
                position=int(point.payload["position"]),
                content=str(point.payload["content"]),
                score=float(point.score),
            )
            for point in response.points
        ]
