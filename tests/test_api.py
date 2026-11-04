from fastapi.testclient import TestClient

from financial_twins.api import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_contract() -> None:
    response = client.get("/api/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["manifest"]["count"] == 120
    assert len(data["profiles"]) == 120
    assert data["evaluation"]["passed"] is True
    assert len(data["simulation"]["summaries"]) == 3


def test_spa_cannot_escape_static_root() -> None:
    response = client.get("/%2e%2e/%2e%2e/README.md")
    assert response.status_code == 404


def test_unknown_api_route_is_not_spa_fallback() -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
