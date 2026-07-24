from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.services import monitoring
from app.services.snmp_client import SnmpResult, SupplyReading


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


def test_manual_snmp_check_updates_printer_and_supplies(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeSnmpClient:
        async def check(self, host: str, community: str) -> SnmpResult:
            assert host == "192.0.2.20"
            assert community == "private"
            return SnmpResult(
                description="HP LaserJet test",
                supplies=[SupplyReading(name="Black Cartridge", level_percent=73)],
            )

    monkeypatch.setattr(monitoring, "SnmpClient", FakeSnmpClient)
    create_response = client.post(
        "/printers",
        data={
            "name": "Checked printer",
            "host": "192.0.2.20",
            "model": "HP test",
            "community": "private",
            "enabled": "on",
        },
        follow_redirects=False,
    )
    printer_id = int(create_response.headers["location"].rsplit("/", 1)[-1])

    check_response = client.post(
        f"/printers/{printer_id}/check", follow_redirects=False
    )

    assert check_response.status_code == 303
    assert check_response.headers["location"].endswith("?checked=ok")
    printer = database.get_printer(printer_id)
    assert printer is not None
    assert printer["status"] == "ok"
    assert printer["last_checked_at"] is not None
    supplies = database.list_supplies(printer_id)
    assert len(supplies) == 1
    assert supplies[0]["name"] == "Black Cartridge"
    assert supplies[0]["level_percent"] == 73

    details_response = client.get(check_response.headers["location"])
    assert "Black Cartridge" in details_response.text
    assert "73%" in details_response.text


def test_failed_snmp_check_marks_printer_offline(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingSnmpClient:
        async def check(self, host: str, community: str) -> SnmpResult:
            raise monitoring.SnmpError("No SNMP response received before timeout")

    monkeypatch.setattr(monitoring, "SnmpClient", FailingSnmpClient)
    create_response = client.post(
        "/printers",
        data={
            "name": "Offline printer",
            "host": "192.0.2.30",
            "model": "",
            "community": "public",
            "enabled": "on",
        },
        follow_redirects=False,
    )
    printer_id = int(create_response.headers["location"].rsplit("/", 1)[-1])

    check_response = client.post(
        f"/printers/{printer_id}/check", follow_redirects=False
    )

    assert check_response.headers["location"].endswith("?checked=failed")
    printer = database.get_printer(printer_id)
    assert printer is not None
    assert printer["status"] == "offline"
    events = database.list_events(printer_id=printer_id)
    assert "No SNMP response received before timeout" in events[0]["message"]


def test_low_supply_marks_printer_warning(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class LowSupplySnmpClient:
        async def check(self, host: str, community: str) -> SnmpResult:
            return SnmpResult(
                description="HP LaserJet test",
                supplies=[SupplyReading(name="Black Cartridge", level_percent=12)],
            )

    monkeypatch.setattr(monitoring, "SnmpClient", LowSupplySnmpClient)
    printer_id = database.create_printer(
        {
            "name": "Low toner printer",
            "host": "192.0.2.40",
            "model": "",
            "community": "public",
            "enabled": 1,
        }
    )

    response = client.post(f"/printers/{printer_id}/check", follow_redirects=False)

    assert response.status_code == 303
    printer = database.get_printer(printer_id)
    assert printer is not None
    assert printer["status"] == "warning"
    events = database.list_events(printer_id=printer_id)
    assert "Black Cartridge (12%)" in events[0]["message"]
