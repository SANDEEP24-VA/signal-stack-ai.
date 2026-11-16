from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class JobSchedulerManager:
    """Manager for background jobs and crawling intervals."""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None

    def initialize(self):
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()

    def start(self):
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)


scheduler_manager = JobSchedulerManager()
