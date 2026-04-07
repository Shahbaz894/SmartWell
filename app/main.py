# app/main.py
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# IMPORTANT: Import base_class first to ensure all models are registered 
import app.db.base_class  
from app.db.base import Base
from app.db.session import engine
from app.core.logger import logger
from app.core.exceptions import AppException

# Import all your API routers
from app.api import (
    auth_routes,
    device_routes,
    motor_routes,
    motor_telemetry_routes,
    schedule_routes,
    khata_routes,
)

# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    Includes retry logic to wait for the database to be ready.
    """
    retries = 10
    connected = False
    
    # Debugging: Check if environment variable is actually reaching the app
    db_url = os.getenv("DATABASE_URL", "NOT_SET")
    # Masking password for security in logs
    masked_url = f"{db_url[:20]}...{db_url[-15:]}" if len(db_url) > 35 else db_url
    logger.info(f"🔍 Checking DATABASE_URL: {masked_url}")
    
    if db_url == "NOT_SET":
        logger.critical("❌ FATAL: DATABASE_URL environment variable not set!")
        raise AppException("DATABASE_URL is not configured")
    
    logger.info("🚀 Starting up IoT TubeWell API...")
    
    while retries > 0 and not connected:
        try:
            # Create tables and verify connection
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database connection established and tables verified.")
            connected = True
        except (OperationalError, SQLAlchemyError) as e:
            retries -= 1
            error_snippet = str(e)[:100]
            logger.warning(f"⚠️ Database not ready yet. Error: {error_snippet}. Retrying in 3s... ({retries} attempts left)")
            # Use asyncio.sleep since this is an async function
            await asyncio.sleep(3)
    
    if not connected:
        logger.critical("❌ FATAL: Could not connect to database after 10 attempts.")
        raise AppException("Database initialization failed permanently.")

    yield  # --- Application is now running ---

    logger.info("🛑 Shutting down IoT TubeWell API...")


# --- Create FastAPI App ---
app = FastAPI(
    title="IoT TubeWell API", 
    description="Backend for ESP32 and Flutter Integration",
    version="1.0.0",
    lifespan=lifespan
)

# --- Register Routers ---
# Note: I've added prefixes to keep your API organized
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(device_routes.router, prefix="/devices", tags=["Devices"])
app.include_router(motor_routes.router, prefix="/motors", tags=["Motors"])
app.include_router(motor_telemetry_routes.router, prefix="/telemetry", tags=["Telemetry"])
app.include_router(schedule_routes.router, prefix="/schedules", tags=["Schedules"])
app.include_router(khata_routes.router, prefix="/khata", tags=["Accounting"])


# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"🔥 Unhandled Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "message": str(exc) if not isinstance(exc, AppException) else "Application Logic Error"
        },
    )


# --- Root / Health Check Endpoint ---
@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "IoT TubeWell Backend is running",
        "database": "connected"
    }