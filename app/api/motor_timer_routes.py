from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.motor_timer import MotorTimer

from app.schemas.motor_timer_schema import (
    MotorTimerCreate,
)

from app.services.motor_timer_service import (
    MotorTimerService,
)

router = APIRouter(
    prefix="/motor-timer",
    tags=["Motor Timer"],
)


@router.post("/start")
async def start_timer(
    payload: MotorTimerCreate,
    db: Session = Depends(get_db),
):

    timer = await MotorTimerService.start_timer(
        db=db,
        device_id=payload.device_id,
        customer_name=payload.customer_name,
        start_time=payload.start_time,
        stop_time=payload.stop_time,
    )

    return {
        "success": True,
        "message": "Motor timer started",
        "data": timer,
    }


@router.post("/stop/{device_id}")
def stop_now(
    device_id: str,
    db: Session = Depends(get_db),
):

    timer = MotorTimerService.stop_now(
        db,
        device_id,
    )

    return {
        "success": True,
        "message": "Motor stopped",
        "data": timer,
    }
    
    
    
@router.get("/status/{device_id}")
def get_timer_status(
    device_id: str,
    db: Session = Depends(get_db),
):

    timer = (
        db.query(MotorTimer)
        .filter(
            MotorTimer.device_id == device_id,
            MotorTimer.is_running == True,
        )
        .first()
    )

    if not timer:
        return {
            "running": False
        }

    return {
        "running": True,
        "start_time": timer.start_time,
        "stop_time": timer.stop_time,
        "duration_minutes": timer.duration_minutes,
        "customer_name": timer.customer_name,
    }