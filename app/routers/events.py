"""Monitoring event routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database import list_events, list_printers

router = APIRouter(prefix="/events", tags=["events"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)


@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def events_page(
    request: Request,
    printer_id: int | None = None,
    event_type: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={
            "events": list_events(printer_id, event_type),
            "printers": list_printers(),
            "selected_printer_id": printer_id,
            "selected_event_type": event_type or "",
        },
    )
