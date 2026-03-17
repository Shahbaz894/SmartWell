# app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
import app.db.base_class   # MUST be before create_all
from app.db.base import Base
from app.api import (
    auth_routes,
    device_routes,
    motor_routes,
    motor_telemetry_routes,
    schedule_routes,
    khata_routes,
)
from app.db.session import engine

import app.db.base_class  # loads all models
from app.core.logger import logger
from app.core.exceptions import AppException


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup code
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (if not exist)")
        yield
    except SQLAlchemyError as e:
        logger.error("Database initialization failed: %s", str(e))
        raise AppException("Database initialization failed")
    finally:
        # Shutdown code
        logger.info("Shutdown cleanup (if any)")


# Create FastAPI app
app = FastAPI(title="IoT TubeWell API", lifespan=lifespan)


# Routers
app.include_router(auth_routes.router)
app.include_router(device_routes.router)
app.include_router(motor_routes.router)
app.include_router(schedule_routes.router)
app.include_router(khata_routes.router)
app.include_router(motor_telemetry_routes.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("🔥 ERROR:", str(exc))   # 👈 add this
    logger.error("Unhandled exception: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},   # 👈 show real error
    )


# Root endpoint
@app.get("/")
async def root():
    try:
        logger.info("Root endpoint accessed")
        return {"message": "IoT TubeWell Backend Running"}
    except Exception as e:
        logger.error("Root endpoint failed: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to load backend status"},
        )