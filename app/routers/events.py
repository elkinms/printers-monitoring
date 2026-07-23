"""Monitoring event routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/events", tags=["events"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)


@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def events_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="events.html")
