import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

# Import database and models
from app.db.base_class import Base
from app.db.session import engine
import app.db.base 

# Import services and routers
from app.api import (
    auth_routes, device_routes, khata_routes, motor_routes,
    motor_telemetry_routes, schedule_routes, user_routes, vfd_control_routes,
)
from app.api.motor_timer_routes import router as motor_timer_routes
from app.services.mqtt_telemetry_consumer_service import MQTTTelemetryConsumerService
from app.services.mqtt_service import MQTTService
from app.core.logger import logger
from app.core.scheduler import start_scheduler, stop_scheduler

# GLOBAL REFERENCE
mqtt_consumer_ref = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with robust error handling."""
    global mqtt_consumer_ref
    
    # 1. DATABASE INITIALIZATION
    logger.info("Starting Database Initialization...")
    try:
        def init_db():
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
        
        await asyncio.to_thread(init_db)
        logger.info("Database connection and schema verified.")
    except Exception as e:
        logger.critical(f"Database setup failed: {e}")
        raise RuntimeError("Database initialization failed")

    # 2. BACKGROUND SERVICE INITIALIZATION
    try:
        logger.info("Initializing MQTT Services...")
        _ = MQTTService()
        consumer = MQTTTelemetryConsumerService()
        
        # Start in background to prevent blocking the Event Loop
        consumer.start()
        mqtt_consumer_ref = consumer
        app.state.mqtt_consumer = consumer
        
        logger.info("MQTT Consumer started.")
        start_scheduler()
        logger.info("System Services successfully launched.")
    except Exception as e:
        logger.error(f"MQTT/Background service failure: {e}", exc_info=True)

    yield 

    # 3. GRACEFUL SHUTDOWN
    logger.info("Shutting down services...")
    if mqtt_consumer_ref:
        mqtt_consumer_ref.stop()
    stop_scheduler()

# Initialize FastAPI
app = FastAPI(
    title="IoT TubeWell API", 
    lifespan=lifespan,
    docs_url="/docs",      # Swagger UI ka URL
    openapi_url="/openapi.json" # Open API Schema
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(device_routes.router)
app.include_router(motor_routes.router)
app.include_router(motor_telemetry_routes.router)
app.include_router(schedule_routes.router)
app.include_router(khata_routes.router)
app.include_router(vfd_control_routes.router)
app.include_router(motor_timer_routes)

@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "message": "Backend fully operational"}