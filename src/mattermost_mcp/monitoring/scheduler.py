"""Scheduler for the monitoring system using APScheduler."""

from collections.abc import Awaitable, Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from mattermost_mcp.logging import get_logger

logger = get_logger(__name__)


class MonitoringScheduler:
    """Cron-based scheduler for the monitoring system."""

    def __init__(self, schedule: str, callback: Callable[[], Awaitable[None]]) -> None:
        """Initialize the scheduler.

        Args:
            schedule: Cron expression (e.g., "*/5 * * * *")
            callback: Async function to call on each scheduled run
        """
        self._schedule = schedule
        self._callback = callback
        self._scheduler: AsyncIOScheduler | None = None
        self._task_running = False
        self._job_id = "monitoring_job"

    def _parse_cron(self, schedule: str) -> dict[str, Any]:
        """Parse a cron expression into APScheduler trigger arguments.

        Args:
            schedule: Cron expression (5-part: minute hour day month day_of_week)

        Returns:
            Dictionary of trigger arguments
        """
        parts = schedule.strip().split()

        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {schedule}. Expected 5 parts.")

        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }

    async def _run_callback(self) -> None:
        """Run the callback function with task tracking."""
        if self._task_running:
            logger.warning("Previous monitoring task still running, skipping this run")
            return

        self._task_running = True
        try:
            logger.info("Starting scheduled monitoring run")
            await self._callback()
            logger.info("Completed scheduled monitoring run")
        except Exception as e:
            logger.error("Error in scheduled monitoring run", error=str(e))
        finally:
            self._task_running = False

    def start(self) -> bool:
        """Start the scheduler.

        Returns:
            True if started successfully
        """
        try:
            self._scheduler = AsyncIOScheduler()

            # Parse cron expression and create trigger
            cron_args = self._parse_cron(self._schedule)
            trigger = CronTrigger(**cron_args)

            # Add the job
            self._scheduler.add_job(
                self._run_callback,
                trigger=trigger,
                id=self._job_id,
                replace_existing=True,
            )

            # Start the scheduler
            self._scheduler.start()
            logger.info("Monitoring scheduler started", schedule=self._schedule)
            return True
        except Exception as e:
            logger.error("Failed to start scheduler", error=str(e))
            return False

    def stop(self) -> bool:
        """Stop the scheduler.

        Returns:
            True if stopped successfully
        """
        try:
            if self._scheduler:
                self._scheduler.shutdown(wait=False)
                self._scheduler = None
                logger.info("Monitoring scheduler stopped")
            return True
        except Exception as e:
            logger.error("Failed to stop scheduler", error=str(e))
            return False

    async def run_now(self) -> None:
        """Run the monitoring task immediately."""
        await self._run_callback()

    def is_task_running(self) -> bool:
        """Check if a monitoring task is currently running.

        Returns:
            True if a task is running
        """
        return self._task_running

    def is_scheduler_running(self) -> bool:
        """Check if the scheduler is running.

        Returns:
            True if the scheduler is active
        """
        return self._scheduler is not None and self._scheduler.running
