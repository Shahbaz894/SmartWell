# app/core/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from app.db.session import SessionLocal
from app.services.schedule_service import ScheduleService

def run_scheduler():
    db = SessionLocal()
    service = ScheduleService(db)
    service.check_and_run()
    db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scheduler, "interval", seconds=60)
    scheduler.start()