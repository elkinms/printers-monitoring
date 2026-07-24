"""Small SQLite persistence layer used by the web application."""

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Iterator

from app.config import settings

DATABASE_URL = settings.database_url


def _database_path() -> Path:
    prefix = "sqlite:///"
    if not DATABASE_URL.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported")
    path = Path(DATABASE_URL.removeprefix(prefix))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    database_path = _database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(database_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize_database() -> None:
    """Create the MVP tables and default settings."""
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS printers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL UNIQUE,
                model TEXT NOT NULL DEFAULT '',
                community TEXT NOT NULL DEFAULT 'public',
                enabled INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'unknown',
                last_checked_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS supplies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                printer_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                level_percent INTEGER,
                FOREIGN KEY (printer_id) REFERENCES printers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                printer_id INTEGER,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (printer_id) REFERENCES printers(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        defaults = {
            "poll_interval_minutes": "30",
            "warning_threshold_percent": "20",
            "smtp_host": "",
            "smtp_port": "587",
            "smtp_username": "",
            "smtp_password": "",
            "smtp_from": "",
            "smtp_to": "",
            "smtp_tls": "1",
        }
        db.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            defaults.items(),
        )


def list_printers() -> list[sqlite3.Row]:
    with connection() as db:
        return list(db.execute("SELECT * FROM printers ORDER BY name"))


def get_printer(printer_id: int) -> sqlite3.Row | None:
    with connection() as db:
        return db.execute(
            "SELECT * FROM printers WHERE id = ?", (printer_id,)
        ).fetchone()


def list_supplies(printer_id: int) -> list[sqlite3.Row]:
    with connection() as db:
        return list(
            db.execute(
                "SELECT * FROM supplies WHERE printer_id = ? ORDER BY id",
                (printer_id,),
            )
        )


def create_printer(data: dict[str, object]) -> int:
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        cursor = db.execute(
            """
            INSERT INTO printers(name, host, model, community, enabled, created_at)
            VALUES (:name, :host, :model, :community, :enabled, :created_at)
            """,
            {**data, "created_at": now},
        )
        printer_id = int(cursor.lastrowid)
        db.execute(
            """
            INSERT INTO events(printer_id, event_type, message, created_at)
            VALUES (?, 'info', 'Принтер добавлен', ?)
            """,
            (printer_id, now),
        )
        return printer_id


def update_printer(printer_id: int, data: dict[str, object]) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE printers
            SET name=:name, host=:host, model=:model,
                community=:community, enabled=:enabled
            WHERE id=:id
            """,
            {**data, "id": printer_id},
        )


def delete_printer(printer_id: int) -> None:
    with connection() as db:
        db.execute("DELETE FROM printers WHERE id = ?", (printer_id,))


def record_monitoring_result(
    printer_id: int,
    status: str,
    supplies: list[dict[str, object]] | None,
    message: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        previous = db.execute(
            "SELECT status FROM printers WHERE id = ?", (printer_id,)
        ).fetchone()
        if previous is None:
            return
        db.execute(
            """
            UPDATE printers
            SET status = ?, last_checked_at = ?
            WHERE id = ?
            """,
            (status, now, printer_id),
        )
        if supplies is not None:
            db.execute("DELETE FROM supplies WHERE printer_id = ?", (printer_id,))
            db.executemany(
                """
                INSERT INTO supplies(printer_id, name, level_percent)
                VALUES (?, ?, ?)
                """,
                [
                    (printer_id, supply["name"], supply["level_percent"])
                    for supply in supplies
                ],
            )
        event_type = (
            "error"
            if status in {"offline", "error"}
            else "warning"
            if status == "warning"
            else "recovery"
            if previous["status"] in {"offline", "error", "warning"}
            else "info"
        )
        db.execute(
            """
            INSERT INTO events(printer_id, event_type, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (printer_id, event_type, message, now),
        )


def list_events(
    printer_id: int | None = None, event_type: str | None = None
) -> list[sqlite3.Row]:
    conditions: list[str] = []
    parameters: list[object] = []
    if printer_id is not None:
        conditions.append("events.printer_id = ?")
        parameters.append(printer_id)
    if event_type:
        conditions.append("events.event_type = ?")
        parameters.append(event_type)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with connection() as db:
        return list(
            db.execute(
                f"""
                SELECT events.*, printers.name AS printer_name
                FROM events LEFT JOIN printers ON printers.id = events.printer_id
                {where}
                ORDER BY events.created_at DESC, events.id DESC
                """,
                parameters,
            )
        )


def get_settings() -> dict[str, str]:
    with connection() as db:
        rows = db.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}


def save_settings(values: dict[str, str]) -> None:
    with connection() as db:
        db.executemany(
            """
            INSERT INTO settings(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            values.items(),
        )
