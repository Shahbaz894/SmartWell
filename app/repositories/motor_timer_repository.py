from sqlalchemy.orm import Session

from app.models.motor_timer import MotorTimer


class MotorTimerRepository:

    @staticmethod
    def create(
        db: Session,
        device_id: str,
        customer_name: str,
        start_time,
        stop_time,
        duration_minutes: int,
    ):

        timer = MotorTimer(
            device_id=device_id,
            customer_name=customer_name,
            start_time=start_time,
            stop_time=stop_time,
            duration_minutes=duration_minutes,
            is_running=True,
            is_completed=False,
        )

        db.add(timer)
        db.commit()
        db.refresh(timer)

        return timer

    @staticmethod
    def get_running_timer(
        db: Session,
        device_id: str,
    ):

        return (
            db.query(MotorTimer)
            .filter(
                MotorTimer.device_id == str(device_id),
                MotorTimer.is_running == True,
            )
            .first()
        )

    @staticmethod
    def stop_timer(
        db: Session,
        timer: MotorTimer,
    ):

        timer.is_running = False
        timer.is_completed = True

        db.commit()
        db.refresh(timer)

        return timer