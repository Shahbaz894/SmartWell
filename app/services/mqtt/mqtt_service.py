import json
import paho.mqtt.publish as publish

from app.core.config import settings
from app.core.logger import logger


class MQTTService:

    @staticmethod
    def publish_motor_command(
        device_id: str,
        command: str,
    ):

        topic = f"{settings.MQTT_COMMAND_TOPIC_PREFIX}/{device_id}/command"

        payload = {
            "command": command
        }

        logger.info(f"MQTT SEND => {topic} => {payload}")

        publish.single(
            topic=topic,
            payload=json.dumps(payload),
            hostname=settings.MQTT_BROKER,
            port=settings.MQTT_PORT,
            auth={
                "username": settings.MQTT_USERNAME,
                "password": settings.MQTT_PASSWORD,
            } if settings.MQTT_USERNAME else None,
        )