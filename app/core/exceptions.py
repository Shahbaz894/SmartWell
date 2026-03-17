# app/core/exceptions.py

from fastapi import HTTPException

# Generic base exception for your app
class AppException(HTTPException):
    def __init__(self, status_code: int = 400, detail: str = "Application error"):
        super().__init__(status_code=status_code, detail=detail)

# Not found exception
class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)

# Device-specific exceptions
class DeviceNotFound(NotFoundException):
    def __init__(self):
        super().__init__(detail="Device not found")

class UnauthorizedAccess(AppException):
    def __init__(self):
        super().__init__(status_code=403, detail="Unauthorized access")

class KhataNotFound(NotFoundException):
    def __init__(self):
        super().__init__(detail="Khata entry not found")

class MotorAlreadyRunning(AppException):
    def __init__(self):
        super().__init__(status_code=400, detail="Motor is already running")