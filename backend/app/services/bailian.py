from typing import Any

import httpx
from openai import OpenAI

from app.services.providers import EmbeddingError, RerankError


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


class BailianRerankProvider:
    def __init__(
        self,
        *,
        api_key: str,
        workspace_id: str,
        model: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.url = (
            f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com"
            "/compatible-api/v1/reranks"
        )
        self.client = client or httpx.Client(timeout=30)

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        try:
            response = self.client.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "query": query,
                    "documents": documents,
                    "top_n": len(documents),
                },
            )
            response.raise_for_status()
            rows = response.json()["results"]
            scores = [0.0] * len(documents)
            for row in rows:
                scores[int(row["index"])] = float(row["relevance_score"])
            if len(rows) != len(documents):
                raise RerankError("Rerank provider returned an unexpected result count")
            return scores
        except RerankError:
            raise
        except Exception as exc:
            raise RerankError("Rerank request failed") from exc
