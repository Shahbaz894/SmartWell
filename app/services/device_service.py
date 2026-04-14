# app/services/device_service.py
#
# Device service layer.
# Handles device registration, ownership validation, and retrieval.
#
# ── AppException Usage ────────────────────────────────────────────────────────
#  Always called as AppException(status_code=int, detail=str).
#  Never pass a plain string as the first arg — that crashes on __init__.
# ──────────────────────────────────────────────────────────────────────────────

import secrets

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.device import Device
from app.repositories.device_repo import DeviceRepository
from app.schemas.device_schema import DeviceCreate
from app.core.logger import logger
from app.core.exceptions import AppException


class DeviceService:
    """
    Service layer for Device operations.

    Responsibilities
    ----------------
    - Validate UID uniqueness before insert.
    - Generate a secure device_secret on creation.
    - Enforce ownership on update operations.
    - Delegate all persistence to DeviceRepository.
    """

    def __init__(self, db: Session):
        self.repo = DeviceRepository(db)

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────
    def create_device(self, user_id: str, device_data: DeviceCreate):
        """
        Register a new device for the authenticated user.

        Parameters
        ----------
        user_id     : str          Authenticated user from JWT.
        device_data : DeviceCreate Validated request body.

        Returns
        -------
        Device
            The newly created and committed Device row.

        Raises
        ------
        AppException(400)
            Device UID already exists, or database error during insert.
        """
        try:
            logger.info(
                "Creating device: uid=%s, user_id=%s",
                device_data.device_uid, user_id,
            )

            existing = self.repo.get_by_uid(device_data.device_uid)
            if existing:
                raise AppException(
                    status_code=400,
                    detail=f"Device with UID '{device_data.device_uid}' already exists",
                )

            new_device = Device(
                id            = device_data.device_uid,   # custom PK
                user_id       = user_id,
                device_name   = device_data.device_name,
                device_uid    = device_data.device_uid,
                sim_number    = device_data.sim_number,
                location      = device_data.location,
                device_secret = secrets.token_urlsafe(32),
            )

            created = self.repo.create_device(new_device)
            logger.info(
                "Device created: id=%s, user_id=%s", created.id, user_id
            )
            return created

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error creating device uid=%s: %s", device_data.device_uid,
                exc, exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Database error: failed to create device '{device_data.device_uid}'",
            )

        except Exception as exc:
            logger.error("Unexpected error creating device: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while creating device: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────────────
    def update_device(self, device_id: str, user_id: str, device_data):
        """
        Update editable fields on a device.

        Ownership is verified before any mutation: the device's user_id must
        match the authenticated user's id.

        Parameters
        ----------
        device_id   : str  Primary key of the device to update.
        user_id     : str  Authenticated user from JWT.
        device_data :      Schema object with optional updatable fields.

        Returns
        -------
        Device
            The updated Device row.

        Raises
        ------
        AppException(404)   Device not found.
        AppException(403)   Caller does not own this device.
        AppException(500)   Unexpected database or runtime error.
        """
        try:
            logger.info(
                "Updating device: device_id=%s, user_id=%s", device_id, user_id
            )

            db_device = self.repo.get_by_id(device_id)
            if not db_device:
                raise AppException(
                    status_code=404,
                    detail=f"Device '{device_id}' not found",
                )

            if str(db_device.user_id) != str(user_id):
                logger.warning(
                    "Update denied: device_id=%s, user_id=%s, owner=%s",
                    device_id, user_id, db_device.user_id,
                )
                raise AppException(
                    status_code=403,
                    detail="Access denied: this device does not belong to you",
                )

            if getattr(device_data, "reference_freq", None) is not None:
                db_device.reference_freq = device_data.reference_freq

            updated = self.repo.update_device(db_device)
            logger.info("Device updated: device_id=%s", device_id)
            return updated

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error updating device_id=%s: %s", device_id, exc, exc_info=True
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while updating device '{device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error updating device_id=%s: %s", device_id, exc, exc_info=True
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while updating device: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GET ALL  (for one user)
    # ─────────────────────────────────────────────────────────────────────────
    def get_user_devices(self, user_id: str):
        """
        Return all devices belonging to the authenticated user.

        Parameters
        ----------
        user_id : str   Authenticated user from JWT.

        Returns
        -------
        list[Device]

        Raises
        ------
        AppException(500)   Unexpected database or runtime error.
        """
        try:
            devices = self.repo.get_user_devices(user_id)
            logger.debug(
                "Fetched %d devices for user_id=%s", len(devices), user_id
            )
            return devices

        except Exception as exc:
            logger.error(
                "Error fetching devices for user_id=%s: %s", user_id, exc, exc_info=True
            )
            raise AppException(
                status_code=500,
                detail="Could not fetch devices",
            )