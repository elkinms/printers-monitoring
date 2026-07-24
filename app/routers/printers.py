"""Printer pages and API boundary."""

from pathlib import Path
import sqlite3
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import (
    create_printer,
    delete_printer,
    get_printer,
    list_events,
    list_supplies,
    update_printer,
)
from app.services.monitoring import check_printer

router = APIRouter(prefix="/printers", tags=["printers"])
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parent.parent / "templates"
)


@router.get("/new", response_class=HTMLResponse, include_in_schema=False)
async def printer_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="printer_form.html",
        context={"printer": None, "error": None},
    )


async def _form_data(request: Request) -> dict[str, str]:
    parsed = parse_qs((await request.body()).decode(), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def _printer_values(form: dict[str, str]) -> dict[str, object]:
    return {
        "name": form.get("name", "").strip(),
        "host": form.get("host", "").strip(),
        "model": form.get("model", "").strip(),
        "community": form.get("community", "public").strip() or "public",
        "enabled": int("enabled" in form),
    }


@router.post("", include_in_schema=False)
async def add_printer(request: Request):
    values = _printer_values(await _form_data(request))
    if not values["name"] or not values["host"]:
        return templates.TemplateResponse(
            request=request,
            name="printer_form.html",
            context={"printer": values, "error": "Укажите имя и IP-адрес."},
            status_code=422,
        )
    try:
        printer_id = create_printer(values)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse(
            request=request,
            name="printer_form.html",
            context={"printer": values, "error": "Такой IP-адрес уже добавлен."},
            status_code=409,
        )
    return RedirectResponse(f"/printers/{printer_id}", status_code=303)


@router.get("/{printer_id}", response_class=HTMLResponse, include_in_schema=False)
async def printer_details(request: Request, printer_id: int) -> HTMLResponse:
    printer = get_printer(printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail="Printer not found")
    return templates.TemplateResponse(
        request=request,
        name="printer_details.html",
        context={
            "printer": printer,
            "events": list_events(printer_id=printer_id)[:10],
            "supplies": list_supplies(printer_id),
            "checked": request.query_params.get("checked"),
        },
    )


@router.get("/{printer_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def edit_printer_form(request: Request, printer_id: int) -> HTMLResponse:
    printer = get_printer(printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail="Printer not found")
    return templates.TemplateResponse(
        request=request,
        name="printer_form.html",
        context={"printer": printer, "error": None},
    )


@router.post("/{printer_id}", include_in_schema=False)
async def edit_printer(request: Request, printer_id: int):
    if get_printer(printer_id) is None:
        raise HTTPException(status_code=404, detail="Printer not found")
    values = _printer_values(await _form_data(request))
    if not values["name"] or not values["host"]:
        return templates.TemplateResponse(
            request=request,
            name="printer_form.html",
            context={"printer": {**values, "id": printer_id}, "error": "Укажите имя и IP-адрес."},
            status_code=422,
        )
    try:
        update_printer(printer_id, values)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse(
            request=request,
            name="printer_form.html",
            context={"printer": {**values, "id": printer_id}, "error": "Такой IP-адрес уже добавлен."},
            status_code=409,
        )
    return RedirectResponse(f"/printers/{printer_id}", status_code=303)


@router.post("/{printer_id}/delete", include_in_schema=False)
async def remove_printer(printer_id: int):
    if get_printer(printer_id) is None:
        raise HTTPException(status_code=404, detail="Printer not found")
    delete_printer(printer_id)
    return RedirectResponse("/", status_code=303)


@router.post("/{printer_id}/check", include_in_schema=False)
async def check_printer_now(printer_id: int):
    if get_printer(printer_id) is None:
        raise HTTPException(status_code=404, detail="Printer not found")
    succeeded = await check_printer(printer_id)
    result = "ok" if succeeded else "failed"
    return RedirectResponse(
        f"/printers/{printer_id}?checked={result}", status_code=303
    )
