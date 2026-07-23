"""Monitoring event domain model placeholder."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Event:
    printer_name: str
    message: str
    created_at: datetime
