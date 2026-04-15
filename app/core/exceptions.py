
# app/core/exceptions.py

from fastapi import HTTPException


# =========================================================
# 🔥 BASE EXCEPTION
# =========================================================
class AppException(HTTPException):
    def __init__(
        self,
        status_code: int = 400,
        detail: str = "Application error",
        code: str = "APP_ERROR"
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "code": code,
                "message": detail
            }
        )


# =========================================================
# 📌 GENERIC EXCEPTIONS
# =========================================================
class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(404, detail, code)


class ValidationException(AppException):
    def __init__(self, detail: str = "Invalid input", code: str = "VALIDATION_ERROR"):
        super().__init__(400, detail, code)


class UnauthorizedAccess(AppException):
    def __init__(self):
        super().__init__(403, "Unauthorized access", "UNAUTHORIZED")


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflict occurred", code: str = "CONFLICT"):
        super().__init__(409, detail, code)


# =========================================================
# 🔧 DEVICE EXCEPTIONS
# =========================================================
class DeviceNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Device not found", "DEVICE_NOT_FOUND")


# =========================================================
# 💰 KHATA EXCEPTIONS
# =========================================================
class KhataNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Khata entry not found", "KHATA_NOT_FOUND")


# =========================================================
# ⚙️ MOTOR EXCEPTIONS
# =========================================================
class MotorAlreadyRunning(ConflictException):
    def __init__(self):
        super().__init__("Motor is already running", "MOTOR_ALREADY_RUNNING")


class MotorNotRunning(NotFoundException):
    def __init__(self):
        super().__init__("No running motor found", "MOTOR_NOT_RUNNING")