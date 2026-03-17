# app/api/khata_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.khata_schema import KhataCreate
from app.services.khata_service import KhataService
from app.core.logger import logger
from app.core.exceptions import AppException

router = APIRouter(prefix="/khata", tags=["Khata"])


@router.post("/")
def create_entry(data: KhataCreate, db: Session = Depends(get_db)):
    service = KhataService(db)
    try:
        entry = service.create_entry(data.dict())
        logger.info(
            "Khata entry created: customer=%s, amount=%s",
            data.customer_name,
            data.total_bill
        )
        return entry

    except AppException as e:
        logger.error(
            "Failed to create khata entry for customer=%s: %s",
            data.customer_name,
            str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error creating khata entry for customer=%s: %s",
            data.customer_name,
            str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{entry_id}")
def delete_entry(entry_id: str, db: Session = Depends(get_db)):
    service = KhataService(db)
    try:
        result = service.delete_entry(entry_id)
        if result:
            logger.info("Khata entry deleted: id=%s", entry_id)
            return {"detail": "Entry deleted successfully"}
        else:
            logger.warning("Khata entry not found for deletion: id=%s", entry_id)
            raise HTTPException(status_code=404, detail="Entry not found")
    except AppException as e:
        logger.error("Failed to delete khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error deleting khata entry id=%s: %s", entry_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")