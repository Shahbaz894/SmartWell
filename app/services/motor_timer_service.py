import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from app.repositories.motor_timer_repository import MotorTimerRepository
from app.services.mqtt_service import MQTTService
from app.core.logger import logger
from app.core.exceptions import (
    MotorAlreadyRunning,
    MotorNotRunning,
)

class MotorTimerService:

    @staticmethod
    async def start_timer(
        db: Session,
        device_id: str,
        customer_name: str,
        start_time: datetime,
        stop_time: datetime,
    ):
        running = MotorTimerRepository.get_running_timer(
            db,
            device_id,
        )

        if running:
            raise MotorAlreadyRunning()

        duration_minutes = int(
            (stop_time - start_time).total_seconds() / 60
        )

        if duration_minutes <= 0:
            raise Exception("Invalid duration")

        logger.info(f"START TIMER => device={device_id}")

        # 🔥 Call updated helper utility inside MQTTService
        await MQTTService.publish_motor_command(device_id, "ON")

        timer = MotorTimerRepository.create(
            db=db,
            device_id=device_id,
            customer_name=customer_name,
            start_time=start_time,
            stop_time=stop_time,
            duration_minutes=duration_minutes,
        )

        asyncio.create_task(
            MotorTimerService.auto_stop(
                db,
                timer.id,
                device_id,
                duration_minutes,
            )
        )

        return timer

    @staticmethod
    async def auto_stop(
        db: Session,
        timer_id: int,
        device_id: str,
        duration_minutes: int,
    ):
        try:
            logger.info(f"AUTO STOP WAIT => {duration_minutes} min")
            await asyncio.sleep(duration_minutes * 60)

            running = MotorTimerRepository.get_running_timer(
                db,
                device_id,
            )

            if not running:
                return

            await MQTTService.publish_motor_command(device_id, "OFF")

            MotorTimerRepository.stop_timer(
                db,
                running,
            )

            logger.info(f"MOTOR AUTO STOPPED => {device_id}")

        except Exception as e:
            logger.error(f"AUTO STOP ERROR => {str(e)}")

    @staticmethod
    def stop_now(
        db: Session,
        device_id: str,
    ):
        timer = MotorTimerRepository.get_running_timer(
            db,
            device_id,
        )

        if not timer:
            raise MotorNotRunning()

        MQTTService.publish_motor_command(device_id, "OFF")

        MotorTimerRepository.stop_timer(
            db,
            timer,
        )

        logger.info(f"MOTOR STOPPED MANUALLY => {device_id}")
        return timer