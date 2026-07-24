"""Periodic printer polling with APScheduler."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import get_settings
from app.services.monitoring import check_all_printers

JOB_ID = "poll-printers"


class SchedulerService:
    def __init__(self) -> None:
        self.scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        if self.scheduler is not None:
            return
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.reschedule()

    def reschedule(self) -> None:
        if self.scheduler is None:
            return
        values = get_settings()
        try:
            interval = max(1, int(values.get("poll_interval_minutes", "30")))
        except ValueError:
            interval = 30
        self.scheduler.add_job(
            check_all_printers,
            "interval",
            minutes=interval,
            id=JOB_ID,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def stop(self) -> None:
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None


scheduler_service = SchedulerService()
