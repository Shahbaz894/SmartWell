import json
import threading

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger


class MQTTCommandService:
    """
    MQTT publisher service for motor and VFD control commands.
    """

    def __init__(self):
        self.host = settings.MQTT_BROKER_HOST
        self.port = settings.MQTT_BROKER_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.keepalive = settings.MQTT_KEEPALIVE
        self.qos = settings.MQTT_QOS
        self.topic_prefix = settings.MQTT_COMMAND_TOPIC_PREFIX

        self._lock = threading.Lock()

    def _command_topic(self, device_id: str) -> str:
        """
        Build control topic for a specific device.
        """
        return f"{self.topic_prefix}/{device_id}/commands"

    def _publish(self, topic: str, payload: dict) -> None:
        """
        Publish JSON payload to MQTT broker.
        """
        client = mqtt.Client(client_id="smartwell-command-publisher", clean_session=True)

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
                    "MQTT publish failed: topic=%s, rc=%s",
                    topic,
                    result.rc,
                )
                raise AppException(
                    status_code=502,
                    detail="Failed to publish command to device",
                )

            logger.info("MQTT command published successfully: topic=%s", topic)

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected MQTT publish error: topic=%s, error=%s",
                topic,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=502,
                detail="Unable to communicate with device via MQTT",
            )

        finally:
            try:
                client.disconnect()
            except Exception:
                pass

    def publish_vfd_reset_command(self, device_id: str) -> None:
        """
        Publish VFD reset command.
        """
        payload = {
            "device_id": device_id,
            "command": "RESET_VFD",
        }

        with self._lock:
            self._publish(self._command_topic(device_id), payload)

        logger.info("VFD reset command published: device_id=%s", device_id)

    def publish_reference_frequency_command(
        self,
        device_id: str,
        reference_frequency: float,
    ) -> None:
        """
        Publish VFD reference frequency command.
        """
        payload = {
            "device_id": device_id,
            "command": "SET_REFERENCE_FREQUENCY",
            "reference_frequency": reference_frequency,
        }

        with self._lock:
            self._publish(self._command_topic(device_id), payload)

        logger.info(
            "VFD reference frequency command published: device_id=%s, reference_frequency=%s",
            device_id,
            reference_frequency,
        )