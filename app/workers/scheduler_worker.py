import time
from app.db.session import SessionLocal
from app.services.schedule_service import ScheduleService
from app.core.logger import logger


def run_scheduler():

    while True:

        db = SessionLocal()

        try:

            service = ScheduleService(db)

            service.check_and_run()

            logger.info("Scheduler executed")

        except Exception as e:

            logger.error(f"Scheduler error: {e}")

        finally:

            db.close()

        time.sleep(60)