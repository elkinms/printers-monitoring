from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(
        database, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}"
    )
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Printers Monitoring",
    }


def test_dashboard_is_available(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Printers Monitoring" in response.text


def test_printer_crud_and_event_log(client: TestClient) -> None:
    create_response = client.post(
        "/printers",
        data={
            "name": "Test printer",
            "host": "192.0.2.10",
            "model": "HP test",
            "community": "public",
            "enabled": "on",
        },
        follow_redirects=False,
    )
    assert create_response.status_code == 303
    details_url = create_response.headers["location"]

    details_response = client.get(details_url)
    assert details_response.status_code == 200
    assert "Test printer" in details_response.text

    events_response = client.get("/events")
    assert events_response.status_code == 200
    assert "Принтер добавлен" in events_response.text

    printer_id = int(details_url.rsplit("/", 1)[-1])
    delete_response = client.post(
        f"/printers/{printer_id}/delete", follow_redirects=False
    )
    assert delete_response.status_code == 303


def test_settings_can_be_saved(client: TestClient) -> None:
    response = client.post(
        "/settings",
        data={
            "poll_interval_minutes": "15",
            "warning_threshold_percent": "25",
            "smtp_host": "smtp.example.test",
            "smtp_port": "587",
            "smtp_username": "",
            "smtp_password": "",
            "smtp_from": "",
            "smtp_to": "",
            "smtp_tls": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Настройки сохранены" in response.text
    assert 'value="15"' in response.text
