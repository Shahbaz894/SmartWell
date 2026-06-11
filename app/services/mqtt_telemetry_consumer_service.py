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
        db = None

        try:
            payload_str = msg.payload.decode("utf-8").strip()

            logger.info(
                f"📥 MQTT Message Received | topic={msg.topic} | payload={payload_str}"
            )

            payload = json.loads(payload_str)

            # Expected topic:
            # tubewell/<device_uid>/telemetry
            parts = msg.topic.split("/")

            if len(parts) < 3:
                logger.error(
                    f"❌ Invalid MQTT topic format: {msg.topic}"
                )
                return

            device_uid = parts[1]

            logger.info(
                f"🔍 Processing telemetry for device_uid={device_uid}"
            )

            db = SessionLocal()

            telemetry = self.service.create_telemetry_from_mqtt(
                db=db,
                device_uid=device_uid,
                payload=payload,
            )

            logger.info(
                f"✅ Telemetry stored successfully | "
                f"telemetry_id={telemetry.id} | "
                f"device_uid={device_uid}"
            )

        except json.JSONDecodeError as exc:
            logger.error(
                f"❌ Invalid JSON payload on topic {msg.topic}: {exc}",
                exc_info=True,
            )

        except Exception as exc:
            logger.error(
                f"❌ Error processing MQTT message | "
                f"topic={msg.topic} | error={exc}",
                exc_info=True,
            )

        finally:
            if db:
                db.close()
    def stop(self):
        logger.info("Stopping MQTT Consumer...")
        self.client.loop_stop()
        self.client.disconnect()