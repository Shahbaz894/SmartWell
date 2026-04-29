# main.py
#
# FastAPI application entry point.
# Handles startup and shutdown lifecycle, router registration,
# database initialization, scheduler startup, and global exception handling.
#
# ── Router Prefixes ───────────────────────────────────────────────────────────
#  Each router already declares its own prefix internally.
#  DO NOT add prefix again here.
#
#  auth_routes             → prefix="/auth"
#  device_routes           → prefix="/devices"
#  motor_routes            → prefix="/motor"
#  motor_telemetry_routes  → prefix="/telemetry"
#  schedule_routes         → prefix="/schedule"
#  khata_routes            → prefix="/khata"
#  vfd_control_routes      → prefix="/vfd"
# ──────────────────────────────────────────────────────────────────────────────

import asyncio
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from app.db.base import Base  # This now contains all your models!
from app.db.session import engine
from app.api import user_routes

import app.db.base_class
from app.api import (
    auth_routes,
    device_routes,
    motor_routes,
    motor_telemetry_routes,
    schedule_routes,
    khata_routes,
    vfd_control_routes,
)
from app.core.config import settings
from app.core.logger import logger
from app.db.base import Base
from app.db.session import engine
from app.core.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup flow:
    - validate DATABASE_URL
    - check database connectivity with retries
    - create tables if needed
    - start scheduler

    Shutdown flow:
    - stop scheduler
    - log graceful shutdown
    """
    db_url = settings.DATABASE_URL
    masked_host = db_url.split("@")[-1] if db_url and "@" in db_url else "NOT_SET"

    retries = 10
    retry_delay_seconds = 3
    connected = False

    logger.info("Starting IoT TubeWell API")
    logger.info("Checking database host: %s", masked_host)

    if not db_url:
        logger.critical("FATAL: DATABASE_URL is not configured")
        raise RuntimeError("DATABASE_URL is not configured")

    while retries > 0 and not connected:
        try:
            def check_db():
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    Base.metadata.create_all(bind=engine)

            await asyncio.get_running_loop().run_in_executor(None, check_db)

            connected = True
            logger.info("Database connection established and tables verified")

        except (OperationalError, SQLAlchemyError) as exc:
            retries -= 1
            logger.warning(
                "Database connection failed (%s retries left): %s. Retrying in %ss",
                retries,
                exc,
                retry_delay_seconds,
            )
            await asyncio.sleep(retry_delay_seconds)

        except Exception as exc:
            logger.critical(
                "Unexpected database initialization error: %s",
                exc,
                exc_info=True,
            )
            raise RuntimeError("Unexpected database initialization error") from exc

    if not connected:
        logger.critical("FATAL: Could not connect to database after all retries")
        raise RuntimeError("Database initialization failed permanently")

    try:
        start_scheduler()
        logger.info("Scheduler started successfully")
    except Exception as exc:
        logger.critical(
            "FATAL: Failed to start scheduler: %s",
            exc,
            exc_info=True,
        )
        raise RuntimeError("Failed to start scheduler") from exc

    try:
        yield

    finally:
        logger.info("Shutting down IoT TubeWell API")

        try:
            stop_scheduler()
            logger.info("Scheduler stopped successfully")
        except Exception as exc:
            logger.error(
                "Failed to stop scheduler cleanly: %s",
                exc,
                exc_info=True,
            )


app = FastAPI(
    title="IoT TubeWell API",
    description="Backend for ESP32, VFD, HTTP, and Flutter integration",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.1.8:3000",
        "http://157.245.55.83:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── Routers ───────────────────────────────────────────────────────────────────


app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(device_routes.router)
app.include_router(motor_routes.router)
app.include_router(motor_telemetry_routes.router)
app.include_router(schedule_routes.router)
app.include_router(khata_routes.router)
app.include_router(vfd_control_routes.router)

# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for truly unhandled exceptions.

    AppException and HTTPException are normally handled by FastAPI before
    reaching this point.
    """
    logger.error(
        "Unhandled exception on path=%s error=%s",
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "path": request.url.path,
        },
    )

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """
    Health check endpoint.
    """
    return {
        "status": "online",
        "message": "IoT TubeWell Backend is running",
    }