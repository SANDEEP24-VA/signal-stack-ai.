from starlette.testclient import TestClient


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Signal Stack AI"
    assert data["status"] == "online"


def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"]["connected"] is True
    assert data["database"]["type"] == "sqlite"
    assert "gemini" in data["ai_providers"]
    assert "ollama" in data["ai_providers"]


def test_not_found_handling(client: TestClient):
    response = client.get("/api/nonexistent-endpoint")
    assert response.status_code == 404
