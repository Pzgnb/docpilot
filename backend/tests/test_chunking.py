import pytest

from app.services.chunking import chunk_text


def test_chunks_are_ordered_and_overlap():
    chunks = chunk_text("甲" * 1000, "doc-1", chunk_size=600, overlap=100)

    assert [(chunk.char_start, chunk.char_end) for chunk in chunks] == [
        (0, 600),
        (500, 1000),
    ]
    assert [chunk.position for chunk in chunks] == [0, 1]
    assert all(chunk.document_id == "doc-1" for chunk in chunks)
    assert len({chunk.id for chunk in chunks}) == 2


def test_empty_text_produces_no_chunks():
    assert chunk_text("", "doc-1") == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (100, -1), (100, 100), (100, 101)],
)
def test_invalid_chunk_settings_are_rejected(chunk_size: int, overlap: int):
    with pytest.raises(ValueError):
        chunk_text("content", "doc-1", chunk_size=chunk_size, overlap=overlap)
