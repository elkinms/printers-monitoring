"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import initialize_database
from app.routers import dashboard, events, printers, settings as settings_router
from app.services.scheduler import scheduler_service

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    scheduler_service.start()
    try:
        yield
    finally:
        scheduler_service.stop()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.mount(
        "/static",
        StaticFiles(directory=BASE_DIR / "static"),
        name="static",
    )
    application.include_router(dashboard.router)
    application.include_router(printers.router)
    application.include_router(events.router)
    application.include_router(settings_router.router)
    return application


app = create_app()
