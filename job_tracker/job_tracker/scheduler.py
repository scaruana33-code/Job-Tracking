"""
Refresh-on-cadence engine (APScheduler). Runs the full pipeline on the cron
schedule in config.py (default: Monday 07:00 America/New_York).

Run:  python -m job_tracker.scheduler
"""
from __future__ import annotations

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import CONFIG
from .pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("scheduler")


def start() -> None:
    sched = BlockingScheduler(timezone=CONFIG.timezone)
    trigger = CronTrigger(
        day_of_week=CONFIG.refresh_cron["day_of_week"],
        hour=CONFIG.refresh_cron["hour"],
        minute=CONFIG.refresh_cron["minute"],
        timezone=CONFIG.timezone,
    )
    sched.add_job(run_pipeline, trigger, id="weekly_refresh", max_instances=1, coalesce=True)
    log.info(
        "Scheduled weekly refresh: %s at %s:%s (%s)",
        CONFIG.refresh_cron["day_of_week"],
        CONFIG.refresh_cron["hour"],
        CONFIG.refresh_cron["minute"].zfill(2),
        CONFIG.timezone,
    )

    log.info("Running an initial refresh now...")
    run_pipeline()

    def _shutdown(*_):
        log.info("Shutting down scheduler.")
        sched.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    sched.start()


if __name__ == "__main__":
    start()
