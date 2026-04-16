import json
from typing import Any, Dict

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger


class MQTTService:
    """
    MQTT publisher service for sending device commands.

    Topic format:
        {MQTT_TOPIC_PREFIX}/{device_id}/motor/control

    Example:
        smartwell/devices/device123/motor/control
    """

    def __init__(self):
        self.host = settings.MQTT_BROKER_HOST
        self.port = settings.MQTT_BROKER_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.keepalive = settings.MQTT_KEEPALIVE
        self.qos = settings.MQTT_QOS
        self.topic_prefix = settings.MQTT_TOPIC_PREFIX

    def _build_topic(self, device_id: str) -> str:
        """
        Build MQTT topic for the given device motor control channel.
        """
        return f"{self.topic_prefix}/{device_id}/motor/control"

    def publish_motor_command(
        self,
        device_id: str,
        command: str,
        trigger_type: str,
        operator_name: str,
    ) -> None:
        """
        Publish a motor ON/OFF command for a specific device.

        Args:
            device_id: Unique device identifier.
            command: ON or OFF.
            trigger_type: manual or schedule.
            operator_name: Name entered from frontend.

        Raises:
            AppException: If MQTT publish fails.
        """
        normalized_command = command.strip().upper()
        if normalized_command not in {"ON", "OFF"}:
            raise AppException(status_code=400, detail="Invalid motor command")

        topic = self._build_topic(device_id)

        payload: Dict[str, Any] = {
            "device_id": device_id,
            "command": normalized_command,
            "trigger_type": trigger_type,
            "operator_name": operator_name,
        }

        client = mqtt.Client()

        if self.username:
            client.username_pw_set(self.username, self.password)

        try:
            client.connect(self.host, self.port, self.keepalive)

            result = client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=self.qos,
                retain=False,
            )

            result.wait_for_publish()

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(
                    "MQTT publish failed: device_id=%s, topic=%s, rc=%s",
                    device_id,
                    topic,
                    result.rc,
                )
                raise AppException(
                    status_code=502,
                    detail=f"Failed to publish motor command for device '{device_id}'",
                )

            logger.info(
                "MQTT motor command published successfully: device_id=%s, topic=%s, command=%s",
                device_id,
                topic,
                normalized_command,
            )

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected MQTT error: device_id=%s, command=%s, error=%s",
                device_id,
                normalized_command,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=502,
                detail=f"Unable to communicate with device '{device_id}' via MQTT",
            )

        finally:
            try:
                client.disconnect()
            except Exception:
                pass