from typing import Any

from openai import OpenAI

from app.services.providers import EmbeddingError


class BailianEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str,
        client: Any | None = None,
    ) -> None:
        self.client = client or OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        try:
            for start in range(0, len(texts), 10):
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts[start : start + 10],
                )
                rows = list(response.data)
                if rows and all(hasattr(row, "index") for row in rows):
                    rows.sort(key=lambda row: row.index)
                vectors.extend(row.embedding for row in rows)
        except Exception as exc:
            raise EmbeddingError("Embedding request failed") from exc
        if len(vectors) != len(texts):
            raise EmbeddingError("Embedding provider returned an unexpected vector count")
        return vectors
