"""Application configuration."""

from dataclasses import dataclass
import os
from pathlib import Path
import sys


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def application_directory() -> Path:
    """Return the directory that contains the executable or project."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


DEFAULT_DATABASE_URL = f"sqlite:///{application_directory() / 'data' / 'printers.db'}"


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("PRINTERS_APP_NAME", "Printers Monitoring")
    debug: bool = _as_bool(os.getenv("PRINTERS_DEBUG", "false"))
    host: str = os.getenv("PRINTERS_HOST", "127.0.0.1")
    port: int = int(os.getenv("PRINTERS_PORT", "8000"))
    database_url: str = os.getenv(
        "PRINTERS_DATABASE_URL", DEFAULT_DATABASE_URL
    )
    log_level: str = os.getenv("PRINTERS_LOG_LEVEL", "INFO")


settings = Settings()
