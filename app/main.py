import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events with robust DB retry logic.
    """
    retries = 10
    connected = False
    
    db_url = os.getenv("DATABASE_URL", "NOT_SET")
    # Improved masking for logs
    masked_url = f"{db_url.split('@')[-1]}" if "@" in db_url else db_url
    logger.info(f"🔍 Checking DB Host: {masked_url}")
    
    if db_url == "NOT_SET":
        logger.critical("❌ FATAL: DATABASE_URL environment variable not set!")
        raise AppException("DATABASE_URL is not configured")
    
    logger.info("🚀 Starting up IoT TubeWell API...")
    
    while retries > 0 and not connected:
        try:
            # 1. Check if the DB is actually reachable/responsive (Synchronous call wrapped in run_in_executor)
            def check_db():
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    # 2. Synchronous Table Creation (Only if using sync SQLAlchemy)
                    Base.metadata.create_all(bind=engine)
            
            await asyncio.get_event_loop().run_in_executor(None, check_db)
            
            logger.info("✅ Database connection established and tables verified.")
            connected = True
        except (OperationalError, SQLAlchemyError) as e:
            retries -= 1
            error_msg = str(e)
            
            # Specific hint for common issues
            if "password authentication failed" in error_msg:
                logger.error("❌ DB AUTH ERROR: Check your username/password.")
            elif "does not exist" in error_msg:
                logger.error("❌ DB NAME ERROR: The database name in your URL is wrong.")
            
            logger.warning(f"⚠️ Connection failed ({retries} left). Retrying in 3s...")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"🔥 Unexpected error during DB init: {str(e)}")
            break # Stop retrying on non-DB errors
    
    if not connected:
        logger.critical("❌ FATAL: Could not connect to database after retries.")
        raise AppException("Database initialization failed permanently.")

    yield  # --- Application is now running ---

    logger.info("🛑 Shutting down IoT TubeWell API...")


app = FastAPI(
    title="IoT TubeWell API", 
    description="Backend for ESP32 and Flutter Integration",
    version="1.0.0",
    lifespan=lifespan
)

# --- Register Routers ---
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(device_routes.router, prefix="/devices", tags=["Devices"])
app.include_router(motor_routes.router, prefix="/motors", tags=["Motors"])
app.include_router(motor_telemetry_routes.router, prefix="/telemetry", tags=["Telemetry"])
app.include_router(schedule_routes.router, prefix="/schedules", tags=["Schedules"])
app.include_router(khata_routes.router, prefix="/khata", tags=["Accounting"])

# --- Global Exception Handler ---
@app.exception_handler(Exception)
@app.exception_handler(AppException) # Explicitly catch your custom exception too
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"🔥 Unhandled Exception: {str(exc)}")
    
    status_code = 500
    message = "Internal Server Error"
    
    if isinstance(exc, AppException):
        status_code = 400 # Or your preferred status
        message = str(exc)

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "path": request.url.path
        },
    )

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "IoT TubeWell Backend is running",
    }