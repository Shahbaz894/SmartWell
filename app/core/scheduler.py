from apscheduler.schedulers.background import BackgroundScheduler

from app.core.logger import logger
from app.db.session import SessionLocal
from app.services.schedule_service import ScheduleService

_scheduler: BackgroundScheduler | None = None


def run_scheduler():
    """
    Execute periodic schedule evaluation job.

    This checks active schedules and starts or stops motors as needed.
    """
    db = SessionLocal()
    try:
        service = ScheduleService(db)
        service.check_and_run()
    except Exception as exc:
        logger.error(
            "Unexpected scheduler job error: %s",
            exc,
            exc_info=True,
        )
    finally:
        db.close()


def start_scheduler():
    """
    Start APScheduler instance if not already running.
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("Scheduler start skipped: already running")
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_scheduler,
        trigger="interval",
        seconds=60,
        id="device_schedule_runner",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()

    logger.info("Background scheduler started successfully")
    return _scheduler


def stop_scheduler():
    """
    Stop APScheduler instance cleanly if running.
    """
    global _scheduler

    if not _scheduler:
        logger.info("Scheduler stop skipped: scheduler not initialized")
        return

    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped successfully")

    _scheduler = None