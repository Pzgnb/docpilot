def test_health_reports_local_dependencies_without_exposing_secrets(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "qdrant": "not_checked",
        "models": "not_configured",
    }
    assert "api_key" not in response.text.lower()
    assert "sk-" not in response.text.lower()
