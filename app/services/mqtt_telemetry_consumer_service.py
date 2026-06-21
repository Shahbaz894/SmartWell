import json
import logging
import re
from typing import Optional  # Yeh line correct hai
from app.core.config import settings
from app.core.logger import logger
from app.services.motor_telemetry_service import MotorTelemetryService
import paho.mqtt.client as mqtt
from app.db.session import SessionLocal
class MQTTTelemetryConsumerService:
    def __init__(self):
        self.host = settings.MQTT_BROKER
        self.port = int(settings.MQTT_PORT)
        # Use callback_api_version=mqtt.CallbackAPIVersion.VERSION1 for modern Paho
        self.client = mqtt.Client(
            client_id=settings.MQTT_CLIENT_ID, 
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.service = MotorTelemetryService()
        logger.info(f"DEBUG: Initializing MQTT Consumer to {self.host}:{self.port}")

    def start(self):
        try:
            logger.info(f"DEBUG: Connecting to MQTT broker at {self.host}:{self.port}...")
            self.client.connect(self.host, self.port, keepalive=int(settings.MQTT_KEEPALIVE))
            self.client.loop_start()
            logger.info("DEBUG: MQTT loop_start() initiated.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to start MQTT Consumer: {str(e)}")
    def _extract_device_id(self, topic: str) -> Optional[str]:
        """
        Dynamically extracts the device_uid from the topic using settings.
        Pattern expected: PREFIX/device_uid/SUFFIX
        """
        # Dynamic regex pattern creation
        pattern = f"^{settings.MQTT_COMMAND_TOPIC_PREFIX}/([^/]+)/{settings.MQTT_TELEMETRY_TOPIC_SUFFIX}$"
        
        match = re.match(pattern, topic)
        if match:
            return match.group(1)
            
        # Logging for debugging if the topic doesn't match
        logger.warning(f"⚠️ Topic pattern mismatch: {topic} (Expected: {pattern})")
        return None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("DEBUG: MQTT Connected successfully.")
            client.subscribe("tubewell/+/telemetry", qos=0)
            # client.subscribe("#", qos=0)
            logger.info("DEBUG: Subscribed to topic #")
        else:
            logger.error(f"DEBUG: Connection failed with code {rc}")
    def on_message(self, client, userdata, msg):
        db = None
        try:
            # 1. Device ID extract karein (Aapki nayi method use karke)
            device_uid = self._extract_device_id(msg.topic)
            if not device_uid:
                return # Error pehle hi _extract_device_id log kar chuka hoga

            payload_str = msg.payload.decode("utf-8").strip()
            logger.info(f"📥 MQTT Message Received | topic={msg.topic} | device_uid={device_uid}")

            payload = json.loads(payload_str)

            # 2. Database Operations
            db = SessionLocal()
            telemetry = self.service.create_telemetry_from_mqtt(
                db=db,
                device_uid=device_uid,
                payload=payload,
            )
            logger.info(f"✅ Telemetry stored: {device_uid}")

        except Exception as exc:
            logger.error(f"❌ Error in on_message: {exc}", exc_info=True)
        finally:
            if db:
                db.close()
    def stop(self):
        logger.info("Stopping MQTT Consumer...")
        self.client.loop_stop()
        self.client.disconnect()