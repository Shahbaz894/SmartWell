import json
from typing import Any, Optional
import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import AppException

class MQTTService:
    """
    Thread-safe, Long-lived MQTT service for SmartWell Backend.
    Handles Outbound Commands.
    """
    _instance: Optional['MQTTService'] = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MQTTService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.broker = settings.MQTT_BROKER
        self.port = int(settings.MQTT_PORT)
        self.keepalive = int(settings.MQTT_KEEPALIVE)
        self.topic_prefix = settings.MQTT_COMMAND_TOPIC_PREFIX.strip("/")
        
        # Consistent API Versioning
        client_id = "smartwell-backend-shared-publisher"
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
        
        if settings.MQTT_USERNAME:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            
        self.client.on_disconnect = self._on_disconnect
        self._connect_and_start()
        self._initialized = True

    def _connect_and_start(self):
        try:
            logger.info("Initializing persistent MQTT Publisher connection...")
            self.client.connect(self.broker, self.port, self.keepalive)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to initialize global MQTT Publisher: {e}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        logger.warning(f"Shared MQTT Publisher disconnected (rc={reason_code}). Loop thread handles reconnection.")

    def command_topic(self, device_uid: str) -> str:
        return f"{self.topic_prefix}/{device_uid}/motor"

    @classmethod
    def publish_motor_command(cls, device_uid: str, action: str) -> None:
        instance = cls()
        payload = {"command": action.upper(), "action": action.upper()} 
        logger.info(f"Routing command via shared publisher: device={device_uid}, payload={payload}")
        instance.publish_command(device_uid=device_uid, payload=payload)

    def publish_command(self, device_uid: str, payload: dict[str, Any]) -> None:
        topic = self.command_topic(device_uid)
        try:
            # Result object for QOS 1 delivery tracking
            result = self.client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=1,
                retain=False,
            )
            
            # Non-blocking check for buffer success
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"MQTT Publish buffer overflow or error: rc={result.rc}")
            else:
                logger.info(f"🚀 Command dispatched: {topic}")

        except Exception as exc:
            logger.error(f"MQTT crash: {str(exc)}", exc_info=True)
            raise AppException(status_code=502, detail="MQTT delivery failed")