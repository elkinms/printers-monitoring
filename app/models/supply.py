"""Printer supply domain model placeholder."""

from dataclasses import dataclass


@dataclass(slots=True)
class Supply:
    name: str
    level_percent: int | None = None
