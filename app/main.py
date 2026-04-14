# main.py
#
# FastAPI application entry point.
# Handles startup/shutdown lifecycle, router registration,
# and global exception handling.
#
# ── Router Prefixes ───────────────────────────────────────────────────────────
#  Each router already declares its own prefix internally.
#  DO NOT add prefix again here — it would double the path.
#
#  auth_routes      → prefix="/auth"      → /auth/login, /auth/register
#  device_routes    → prefix="/devices"   → /devices/
#  motor_routes     → prefix="/motors"    → /motors/
#  telemetry_routes → prefix="/telemetry" → /telemetry/
#  schedule_routes  → prefix="/schedules" → /schedules/
#  khata_routes     → prefix="/khata"     → /khata/
# ──────────────────────────────────────────────────────────────────────────────

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from app.core.config import settings
from app.core.scheduler import start_scheduler
from app.core.logger import logger
from app.core.exceptions import AppException

import app.db.base_class
from app.db.base import Base
from app.db.session import engine

# Import routers
from app.api import (
    auth_routes,
    device_routes,
    motor_routes,
    motor_telemetry_routes,
    schedule_routes,
    khata_routes,
)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: verify DB connection with retries, create tables, start scheduler.
    Shutdown: log graceful stop.
    """
    db_url    = settings.DATABASE_URL
    masked    = db_url.split("@")[-1] if db_url and "@" in db_url else "NOT_SET"
    retries   = 10
    connected = False

    logger.info("Checking DB host: %s", masked)

    if not db_url:
        logger.critical("FATAL: DATABASE_URL not configured")
        raise AppException(status_code=500, detail="DATABASE_URL is not configured")

    logger.info("Starting IoT TubeWell API...")

    while retries > 0 and not connected:
        try:
            def check_db():
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    Base.metadata.create_all(bind=engine)

            await asyncio.get_event_loop().run_in_executor(None, check_db)
            logger.info("Database connection established and tables verified.")
            connected = True

        except (OperationalError, SQLAlchemyError) as exc:
            retries -= 1
            logger.warning(
                "DB connection failed (%d retries left): %s. Retrying in 3s...",
                retries, exc,
            )
            await asyncio.sleep(3)

    if not connected:
        logger.critical("FATAL: Could not connect to database after all retries.")
        raise AppException(
            status_code=500,
            detail="Database initialization failed permanently.",
        )

    start_scheduler()
    logger.info("Scheduler started.")

    yield  # ── application running ──

    logger.info("Shutting down IoT TubeWell API...")


# ── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "IoT TubeWell API",
    description = "Backend for ESP32 and Flutter Integration",
    version     = "1.0.0",
    lifespan    = lifespan,
)


# ── Routers ───────────────────────────────────────────────────────────────────
#
# Each router owns its prefix — do NOT add prefix here.
# Tags here are optional overrides; removing them uses the router's own tags.

app.include_router(auth_routes.router)
app.include_router(device_routes.router)
app.include_router(motor_routes.router)
app.include_router(motor_telemetry_routes.router)
app.include_router(schedule_routes.router)
app.include_router(khata_routes.router)


# ── Global exception handler ──────────────────────────────────────────────────
#
# AppException extends HTTPException, so FastAPI handles it automatically.
# This handler only catches truly unexpected exceptions that slipped through
# all service-layer try/except blocks.
#
# IMPORTANT: Do NOT re-handle AppException here — doing so would override the
# correct status_code set in the service layer and always return 400 or 500.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unhandled exceptions.
    AppException / HTTPException are handled by FastAPI before reaching here.
    """
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail" : "Internal Server Error",
            "path"   : request.url.path,
        },
    )


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "message": "IoT TubeWell Backend is running"}