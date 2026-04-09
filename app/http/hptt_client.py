import json
import requests
from app.core.config import settings
from app.core.logger import logger

# Replace MQTT broker with HTTP endpoint
HTTP_BASE_URL = settings.DEVICE_HTTP_URL  # e.g., "http://178.128.107.36"

def publish_motor_command_http(device_uid: str, command: str):
    """
    Send motor command via HTTP POST instead of MQTT.
    """
    url = f"{HTTP_BASE_URL}/motor_command"  # endpoint on your device or API
    payload = {
        "device_uid": device_uid,
        "command": command
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()  # Raise exception for HTTP errors
        logger.info(f"HTTP command sent {command} to {device_uid}, response: {response.text}")
    except requests.RequestException as e:
        logger.error(f"Failed to send HTTP command: {e}")