def test_create_list_and_get_knowledge_base(client):
    created = client.post(
        "/api/knowledge-bases",
        json={"name": "  产品手册  ", "description": "公开演示资料"},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["name"] == "产品手册"
    assert payload["description"] == "公开演示资料"
    assert payload["document_count"] == 0

    listed = client.get("/api/knowledge-bases")
    assert listed.status_code == 200
    assert listed.json() == [payload]

    fetched = client.get(f"/api/knowledge-bases/{payload['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == payload


def test_duplicate_name_returns_conflict(client):
    payload = {"name": "产品手册", "description": ""}

    assert client.post("/api/knowledge-bases", json=payload).status_code == 201
    response = client.post("/api/knowledge-bases", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "KNOWLEDGE_BASE_EXISTS"


def test_empty_name_is_rejected(client):
    response = client.post(
        "/api/knowledge-bases",
        json={"name": "   ", "description": ""},
    )

    assert response.status_code == 422


def test_delete_knowledge_base(client):
    created = client.post(
        "/api/knowledge-bases",
        json={"name": "待删除", "description": ""},
    ).json()

    response = client.delete(f"/api/knowledge-bases/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/knowledge-bases/{created['id']}").status_code == 404
