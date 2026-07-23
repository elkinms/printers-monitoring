"""Application configuration."""

from dataclasses import dataclass
import os


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("PRINTERS_APP_NAME", "Printers Monitoring")
    debug: bool = _as_bool(os.getenv("PRINTERS_DEBUG", "false"))
    host: str = os.getenv("PRINTERS_HOST", "127.0.0.1")
    port: int = int(os.getenv("PRINTERS_PORT", "8000"))
    database_url: str = os.getenv(
        "PRINTERS_DATABASE_URL", "sqlite:///./data/printers.db"
    )
    log_level: str = os.getenv("PRINTERS_LOG_LEVEL", "INFO")


settings = Settings()
