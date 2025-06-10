from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import Callable, Optional
from datetime import datetime
import asyncio

class ReminderScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._started = False

    async def start(self):
        # Ensure this is called from within a running event loop
        if not self._started:
            self.scheduler.start()
            self._started = True

    def schedule(self, job_func: Callable, run_time: datetime, job_id: Optional[str] = None) -> None:
        """Schedule a one-time job at a specific datetime."""
        self.scheduler.add_job(job_func, 'date', run_date=run_time, id=job_id)

    def schedule_cron(self, job_func: Callable, cron_kwargs: dict, job_id: Optional[str] = None) -> None:
        """Schedule a recurring job using cron syntax (e.g., {'hour': 9, 'minute': 0})."""
        self.scheduler.add_job(job_func, 'cron', id=job_id, **cron_kwargs)

    def schedule_interval(self, job_func: Callable, seconds: int, job_id: Optional[str] = None) -> None:
        """Schedule a recurring job every N seconds."""
        self.scheduler.add_job(job_func, 'interval', seconds=seconds, id=job_id)

    def cancel(self, job_id: str) -> None:
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

    def load_jobs(self):
        # Implementation to load persisted jobs if needed
        pass

