"""Printer pages and API boundary."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/printers", tags=["printers"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)


@router.get("/new", response_class=HTMLResponse, include_in_schema=False)
async def printer_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="printer_form.html")


@router.get("/{printer_id}", response_class=HTMLResponse, include_in_schema=False)
async def printer_details(request: Request, printer_id: int) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="printer_details.html",
        context={"printer_id": printer_id},
    )
