"""Printer request and response schemas."""

from pydantic import BaseModel, Field


class PrinterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=255)
    enabled: bool = True


class PrinterRead(PrinterCreate):
    id: int
