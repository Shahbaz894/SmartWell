import json
import paho.mqtt.client as mqtt
from app.core.config import settings
from app.core.logger import logger

BROKER = settings.MQTT_BROKER
PORT = settings.MQTT_PORT

client = mqtt.Client()


def connect():

    client.connect(BROKER, PORT, 60)

    logger.info("MQTT connected")


def publish_motor_command(device_uid: str, command: str):

    topic = f"tubewell/{device_uid}/motor"

    payload = {
        "command": command
    }

    client.publish(topic, json.dumps(payload))

    logger.info(f"MQTT command sent {command} to {device_uid}")