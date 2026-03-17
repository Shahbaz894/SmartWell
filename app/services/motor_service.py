# app/services/motor_service.py

from datetime import datetime
from app.repositories.motor_repo import MotorRepository
from app.models.motor_log import MotorLog


class MotorService:

    def __init__(self, db):
        self.repo = MotorRepository(db)

    def start_motor(self, device_id, trigger):

        running = self.repo.get_running_motor(device_id)

        if running:
            return running

        log = MotorLog(
            device_id=device_id,
            start_time=datetime.utcnow(),
            trigger_type=trigger
        )

        return self.repo.create_log(log)

    def stop_motor(self, device_id):

        log = self.repo.get_running_motor(device_id)

        if not log:
            return None

        log.end_time = datetime.utcnow()

        duration = log.end_time - log.start_time
        log.duration_minutes = int(duration.total_seconds() / 60)

        return self.repo.update_log(log)