def create_knowledge_base(client) -> str:
    response = client.post(
        "/api/knowledge-bases",
        json={"name": "产品资料", "description": ""},
    )
    return response.json()["id"]


def test_upload_and_list_document(client):
    knowledge_base_id = create_knowledge_base(client)

    uploaded = client.post(
        f"/api/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("guide.txt", b"Refunds are available for 30 days.", "text/plain")},
    )

    assert uploaded.status_code == 201
    payload = uploaded.json()
    assert payload["filename"] == "guide.txt"
    assert payload["status"] == "pending"
    assert payload["chunk_count"] == 0

    listed = client.get(f"/api/knowledge-bases/{knowledge_base_id}/documents")
    assert listed.status_code == 200
    assert listed.json() == [payload]


def test_upload_rejects_unsupported_document(client):
    knowledge_base_id = create_knowledge_base(client)

    response = client.post(
        f"/api/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("bad.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "UNSUPPORTED_DOCUMENT"


def test_delete_document_removes_file_and_vectors(client):
    from tests.fakes import FakeVectorStore

    knowledge_base_id = create_knowledge_base(client)
    document = client.post(
        f"/api/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("guide.txt", b"content", "text/plain")},
    ).json()
    store = FakeVectorStore()
    client.app.state.vector_store = store

    response = client.delete(f"/api/documents/{document['id']}")

    assert response.status_code == 204
    assert store.deleted_document_ids == [document["id"]]
    assert client.get(f"/api/knowledge-bases/{knowledge_base_id}/documents").json() == []


def test_process_and_retry_replace_existing_chunks(client):
    from sqlalchemy import func, select

    from app.db.models import DocumentChunk
    from tests.fakes import FakeEmbeddingProvider, FakeVectorStore

    knowledge_base_id = create_knowledge_base(client)
    document = client.post(
        f"/api/knowledge-bases/{knowledge_base_id}/documents",
        files={
            "file": (
                "guide.txt",
                "退款期限为30天。".encode("utf-8") * 100,
                "text/plain",
            )
        },
    ).json()
    store = FakeVectorStore()
    client.app.state.embedding_provider = FakeEmbeddingProvider()
    client.app.state.vector_store = store

    processed = client.post(f"/api/documents/{document['id']}/process")
    retried = client.post(f"/api/documents/{document['id']}/retry")

    assert processed.status_code == 200
    assert retried.status_code == 200
    assert retried.json()["status"] == "ready"
    assert len(store.rows) == retried.json()["chunk_count"]
    assert store.deleted_document_ids == [document["id"], document["id"]]
    with client.app.state.database.session_factory() as session:
        chunk_count = session.scalar(select(func.count()).select_from(DocumentChunk))
    assert chunk_count == retried.json()["chunk_count"]
