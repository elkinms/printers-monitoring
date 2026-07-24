"""Application settings routes."""

from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import get_settings, save_settings
from app.services.scheduler import scheduler_service

router = APIRouter(prefix="/settings", tags=["settings"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)


@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"settings": get_settings(), "saved": request.query_params.get("saved")},
    )


@router.post("", include_in_schema=False)
async def update_settings(request: Request):
    parsed = parse_qs((await request.body()).decode(), keep_blank_values=True)
    values = {key: items[-1].strip() for key, items in parsed.items()}
    values["smtp_tls"] = "1" if "smtp_tls" in values else "0"
    save_settings(values)
    scheduler_service.reschedule()
    return RedirectResponse("/settings?saved=1", status_code=303)
