# # app/repositories/motor_repo.py

# from sqlalchemy.orm import Session
# from sqlalchemy.exc import SQLAlchemyError
# from app.models.motor_log import MotorLog
# from app.core.logger import logger
# from app.core.exceptions import AppException, NotFoundException


# class MotorRepository:

#     def __init__(self, db: Session):
#         self.db = db

#     def create_log(self, log: MotorLog):
#         try:
#             self.db.add(log)
#             self.db.commit()
#             self.db.refresh(log)
#             logger.info(
#                 "Motor log created: id=%s, device_id=%s, trigger_type=%s",
#                 log.id,
#                 log.device_id,
#                 log.trigger_type
#             )
#             return log
#         except SQLAlchemyError as e:
#             self.db.rollback()
#             logger.error(
#                 "Failed to create motor log for device %s: %s",
#                 log.device_id,
#                 str(e)
#             )
#             raise AppException(status_code=500, detail=f"Database error: failed to create motor log for device {log.device_id}")
            

#     def get_running_motor(self, device_id: str):
#         try:
#             running = (
#                 self.db.query(MotorLog)
#                 .filter(MotorLog.device_id == device_id, MotorLog.end_time == None)
#                 .first()
#             )
#             if running:
#                 logger.info("Found running motor log: id=%s, device_id=%s", running.id, device_id)
#             else:
#                 logger.info("No running motor log found for device_id=%s", device_id)
#             return running
#         except SQLAlchemyError as e:
#             logger.error("Failed to fetch running motor log for device %s: %s", device_id, str(e))
#             raise AppException(status_code=500, detail=f"Database error: failed to fetch running motor log for device {device_id}")

#     def update_log(self, log: MotorLog):
#         try:
#             self.db.commit()
#             self.db.refresh(log)
#             logger.info("Motor log updated: id=%s, device_id=%s", log.id, log.device_id)
#             return log
#         except SQLAlchemyError as e:
#             self.db.rollback()
#             logger.error("Failed to update motor log id=%s for device %s: %s", log.id, log.device_id, str(e))
#             raise AppException(status_code=500, detail=f"Database error: failed to update motor log id {log.id}")

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.motor_log import MotorLog
from app.core.logger import logger
from app.core.exceptions import AppException


class MotorRepository:

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────
    def create_log(self, log: MotorLog):
        try:
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)

            logger.info(
                "Motor log created: id=%s, device_id=%s, trigger_type=%s",
                log.id,
                log.device_id,
                log.trigger_type
            )
            return log

        except SQLAlchemyError:
            self.db.rollback()
            logger.error(
                "DB ERROR creating motor log: device=%s",
                log.device_id,
                exc_info=True   # 🔥 IMPORTANT
            )
            raise AppException(
                status_code=500,
                detail=f"Database error: failed to create motor log for device {log.device_id}"
            )

    # ─────────────────────────────────────────────────────────────
    # GET RUNNING MOTOR
    # ─────────────────────────────────────────────────────────────
   
    def get_running_motor(self, device_id: str):
        try:
            running = (
                self.db.query(MotorLog)
                .filter(
                    MotorLog.device_id == device_id,
                    MotorLog.end_time.is_(None)
                )
                .first()
            )
            return running

        except Exception as e:  # ← catch ALL exceptions temporarily
            logger.error("REAL ERROR: %s", repr(e), exc_info=True)  # ← repr gives full details
            raise AppException(
                status_code=500,
                detail=repr(e)  # ← return real error in response temporarily
            )

    # ─────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────
    def update_log(self, log: MotorLog):
        try:
            self.db.commit()
            self.db.refresh(log)

            logger.info(
                "Motor log updated: id=%s, device_id=%s",
                log.id,
                log.device_id
            )
            return log

        except SQLAlchemyError:
            self.db.rollback()
            logger.error(
                "DB ERROR updating motor log: id=%s",
                log.id,
                exc_info=True
            )
            raise AppException(
                status_code=500,
                detail=f"Database error: failed to update motor log id {log.id}"
            )