import asyncio
from contextlib import asynccontextmanager
import app.db.base_class  # noqa: F401 — registers all models with Base.metadata

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

# Import your services and routers
from app.api import (
    auth_routes, device_routes, khata_routes, motor_routes,
    motor_telemetry_routes, schedule_routes, user_routes, vfd_control_routes,
)
from app.api.motor_timer_routes import router as motor_timer_routes
from app.services.mqtt_telemetry_consumer_service import MQTTTelemetryConsumerService
from app.services.mqtt_service import MQTTService
from app.core.config import settings
from app.core.logger import logger
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.session import engine

# GLOBAL REFERENCE: Prevents Python Garbage Collection from killing the MQTT thread
mqtt_consumer_ref = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    global mqtt_consumer_ref
    
    # 1. DATABASE INITIALIZATION
    logger.info("Starting IoT TubeWell API Engine...")
    connected = False
    retries = 10
    while retries > 0 and not connected:
        try:
            def check_db():
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            
            await asyncio.get_running_loop().run_in_executor(None, check_db)
            connected = True
            logger.info("Database connection established.")
        except Exception as exc:
            retries -= 1
            logger.warning("Database connection failed (%s retries left): %s", retries, exc)
            await asyncio.sleep(3)

    if not connected:
        logger.critical("FATAL: Could not connect to database.")
        raise RuntimeError("Database initialization failed")

    # 2. BACKGROUND SERVICE INITIALIZATION
    try:
        logger.info("DEBUG: Initializing MQTT Services...")
        
        # A. Shared MQTT Publisher
        _ = MQTTService()
        logger.info("Global MQTT Command Publisher activated.")

        # B. Telemetry Consumer (Persistent Reference)
        consumer = MQTTTelemetryConsumerService()
        consumer.start()
        
        
        
        # INCREASE RETRIES & LOG MORE
        logger.info("Verifying MQTT connection...")
        connected = False
        for i in range(10): # Increase to 10 seconds
            if consumer.client.is_connected():
                connected = True
                logger.info("MQTT Client confirmed connected.")
                break
            await asyncio.sleep(1)
            logger.info(f"Waiting for MQTT... ({i+1}/10)")
            
        if not connected:
            logger.error("MQTT failed to connect in time.")
            # Do not crash here, just warn - or raise if you want strict boot
        mqtt_consumer_ref = consumer
        app.state.mqtt_consumer = consumer
        logger.info("MQTT Telemetry Consumer service finalized.")

        # C. Scheduler
        start_scheduler()
        logger.info("System Scheduler engine launched.")

    except Exception as exc:
        logger.critical(f"FATAL: Background services failed: {exc}", exc_info=True)
        raise RuntimeError("Background service initialization failed")

    yield  # 🏁 App is now running

    # 3. GRACEFUL SHUTDOWN
    logger.info("Shutting down IoT TubeWell API...")
    if mqtt_consumer_ref:
        mqtt_consumer_ref.stop()
        
    stop_scheduler()

# Initialize FastAPI
app = FastAPI(
    title="IoT TubeWell API",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    logger.error("Unhandled exception: path=%s error=%s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "path": request.url.path},
    )

@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "message": "IoT TubeWell Backend Node is fully operational"}