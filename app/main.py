import asyncio
from contextlib import asynccontextmanager

import app.db.base_class  # noqa: F401 — registers all models with Base.metadata

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.api.motor_timer_routes import router as motor_timer_routes
from app.services.mqtt_telemetry_consumer_service import MQTTTelemetryConsumerService
from app.services.mqtt_service import MQTTService  # 🎯 Added out-bound command pipeline

from app.api import (
    auth_routes,
    device_routes,
    khata_routes,
    motor_routes,
    motor_telemetry_routes,
    schedule_routes,
    user_routes,
    vfd_control_routes,
)
from app.core.config import settings
from app.core.logger import logger
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:
    - Validate DATABASE_URL
    - Check database connectivity with retries
    - Create tables if needed
    - Initialize persistent MQTT Command Publisher Singletons
    - Spawn Background Telemetry Consumer Thread
    - Start scheduler

    Shutdown:
    - Stop MQTT telemetry consumer loop safely
    - Stop scheduler engine clear resources
    """
    db_url = settings.DATABASE_URL
    masked_host = db_url.split("@")[-1] if db_url and "@" in db_url else "NOT_SET"

    retries = 10
    retry_delay_seconds = 3
    connected = False

    logger.info("Starting IoT TubeWell API Engine...")
    logger.info("Checking database host status: %s", masked_host)

    if not db_url:
        logger.critical("FATAL: DATABASE_URL is not configured inside system variables.")
        raise RuntimeError("DATABASE_URL is not configured")

    while retries > 0 and not connected:
        try:
            def check_db():
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    Base.metadata.create_all(bind=engine)

            await asyncio.get_running_loop().run_in_executor(None, check_db)
            connected = True
            logger.info("Database connection established and tables verified successfully.")

        except (OperationalError, SQLAlchemyError) as exc:
            retries -= 1
            logger.warning(
                "Database connection failed (%s retries left): %s. Retrying in %ss",
                retries,
                exc,
                retry_delay_seconds,
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
        logger.critical("FATAL: Could not connect to database container pool after all retries.")
        raise RuntimeError("Database initialization failed permanently")

    # 🚀 MQTT INITIALIZATION ZONE (Only after DB verification is completely done)
    try:
        # 1. Initialize persistent publisher singletons (Commands flow seamlessly)
        _ = MQTTService()
        logger.info("Shared Global MQTT Command Publisher Engine activated.")

        # 2. Spawn and setup background telemetry pipeline listener (DB dynamic entries)
        app.state.mqtt_consumer = MQTTTelemetryConsumerService()
        app.state.mqtt_consumer.start()
        logger.info("Background Telemetry Consumer Process Thread Spawned successfully.")

        # 3. Trigger Cron schedules triggers engines
        start_scheduler()
        logger.info("System Scheduler engine launched successfully.")

    except Exception as exc:
        logger.critical(
            "FATAL: Failed to start background network/scheduling services: %s",
            exc,
            exc_info=True,
        )
        raise RuntimeError("Failed to start background services") from exc

    try:
        yield  # 🏁 Main FastAPI application incoming requests threads operate here
    finally:
        logger.info("Shutting down IoT TubeWell API gracefully...")

        # Safe disconnect for consumer thread
        try:
            if hasattr(app.state, "mqtt_consumer"):
                app.state.mqtt_consumer.stop()
                logger.info("MQTT telemetry consumer connection severed safely.")
        except Exception as exc:
            logger.error("Failed to stop MQTT telemetry consumer loop cleanly: %s", exc, exc_info=True)

        # Safe disconnect for scheduler engine
        try:
            stop_scheduler()
            logger.info("System Scheduler engine stopped successfully.")
        except Exception as exc:
            logger.error("Failed to stop scheduler execution cleanly: %s", exc, exc_info=True)


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
        "http://192.168.1.109:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers Mapping Registration ──────────────────────────────────────────────

app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(device_routes.router)
app.include_router(motor_routes.router)
app.include_router(motor_telemetry_routes.router)
app.include_router(schedule_routes.router)
app.include_router(khata_routes.router)
app.include_router(vfd_control_routes.router)
app.include_router(motor_timer_routes)

# ── Global Exception Handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for truly unhandled exceptions.
    AppException and HTTPException are handled by FastAPI before reaching here.
    """
    logger.error(
        "Unhandled exception: path=%s error=%s",
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

# ── Health Check Verification Route ───────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "IoT TubeWell Backend Node is fully operational",
    }