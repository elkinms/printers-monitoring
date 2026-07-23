"""Printer domain model placeholder."""

from dataclasses import dataclass


@dataclass(slots=True)
class Printer:
    name: str
    host: str
    enabled: bool = True
