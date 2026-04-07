# # app/main.py

# from fastapi import FastAPI, Request
# from fastapi.responses import JSONResponse
# from contextlib import asynccontextmanager
# from sqlalchemy.exc import SQLAlchemyError
# import app.db.base_class   # MUST be before create_all
# from app.db.base import Base
# from app.api import (
#     auth_routes,
#     device_routes,
#     motor_routes,
#     motor_telemetry_routes,
#     schedule_routes,
#     khata_routes,
# )
# from app.db.session import engine

# import app.db.base_class  # loads all models
# from app.core.logger import logger
# from app.core.exceptions import AppException


# # Lifespan event handler
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     try:
#         # Startup code
#         Base.metadata.create_all(bind=engine)
#         logger.info("Database tables created (if not exist)")
#         yield
#     except SQLAlchemyError as e:
#         logger.error("Database initialization failed: %s", str(e))
#         raise AppException("Database initialization failed")
#     finally:
#         # Shutdown code
#         logger.info("Shutdown cleanup (if any)")


# # Create FastAPI app
# app = FastAPI(title="IoT TubeWell API", lifespan=lifespan)

# #all api routers
# # Routers
# app.include_router(auth_routes.router)
# app.include_router(device_routes.router)
# app.include_router(motor_routes.router)
# app.include_router(schedule_routes.router)
# app.include_router(khata_routes.router)
# app.include_router(motor_telemetry_routes.router)


# # Global exception handler
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     print("🔥 ERROR:", str(exc))   # 👈 add this
#     logger.error("Unhandled exception: %s", str(exc))
#     return JSONResponse(
#         status_code=500,
#         content={"detail": str(exc)},   # 👈 show real error
#     )


# # Root endpoint
# @app.get("/")
# async def root():
#     try:
#         logger.info("Root endpoint accessed")
#         return {"message": "IoT TubeWell Backend Running"}
#     except Exception as e:
#         logger.error("Root endpoint failed: %s", str(e))
#         return JSONResponse(
#             status_code=500,
#             content={"detail": "Failed to load backend status"},
#         )

# app/main.py
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# IMPORTANT: Import base_class first to ensure all models are registered 
# on the Base.metadata object before we call create_all
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
    retries = 5
    connected = False
    
    logger.info("🚀 Starting up IoT TubeWell API...")
    
    while retries > 0 and not connected:
        try:
            # This command creates tables if they don't exist
            # It also serves as our connection test
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database connection established and tables verified.")
            connected = True
        except (OperationalError, SQLAlchemyError) as e:
            retries -= 1
            logger.warning(f"⚠️ Database not ready yet (Error: {e}). Retrying in 2s... ({retries} attempts left)")
            time.sleep(2)
    
    if not connected:
        logger.critical("❌ FATAL: Could not connect to database. check DATABASE_URL.")
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