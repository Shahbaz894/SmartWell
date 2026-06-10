import json
import logging
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

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("DEBUG: MQTT Connected successfully.")
            client.subscribe("#", qos=0)
            logger.info("DEBUG: Subscribed to topic #")
        else:
            logger.error(f"DEBUG: Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode("utf-8").strip()
            payload = json.loads(payload_str)
            
            parts = msg.topic.split("/")
            # Add this debug line to see if device_uid is what you expect
            logger.info(f"DEBUG: Processing topic={msg.topic}, device_uid={parts[1]}")

            db = SessionLocal()
            try:
                # Add this debug to see the payload being sent to the service
                logger.info(f"DEBUG: Passing payload to service: {payload}")
                self.service.create_telemetry_from_mqtt(
                    db=db,
                    device_uid=parts[1],
                    payload=payload,
                )
                logger.info(f"✅ Telemetry stored for {parts[1]}")
            except Exception as service_exc:
                # Log the specific error from the service layer
                logger.error(f"❌ Service layer error: {service_exc}", exc_info=True)
                raise service_exc
            finally:
                db.close()
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}", exc_info=True)
    def stop(self):
        logger.info("Stopping MQTT Consumer...")
        self.client.loop_stop()
        self.client.disconnect()