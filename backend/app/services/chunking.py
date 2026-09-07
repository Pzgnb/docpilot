from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5


@dataclass(frozen=True)
class TextChunk:
    id: str
    document_id: str
    position: int
    content: str
    char_start: int
    char_end: int


def chunk_text(
    text: str,
    document_id: str,
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size")
    if not text:
        return []

    step = chunk_size - overlap
    chunks: list[TextChunk] = []
    for position, start in enumerate(range(0, len(text), step)):
        end = min(start + chunk_size, len(text))
        chunks.append(
            TextChunk(
                id=str(uuid5(NAMESPACE_URL, f"{document_id}:{position}:{start}:{end}")),
                document_id=document_id,
                position=position,
                content=text[start:end],
                char_start=start,
                char_end=end,
            )
        )
        if end == len(text):
            break
    return chunks
