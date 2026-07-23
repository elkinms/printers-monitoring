from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Printers Monitoring",
    }


def test_dashboard_is_available() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Printers Monitoring" in response.text
