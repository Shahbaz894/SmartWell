import json
import threading

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger


class ScheduleMQTTService:
    """
    MQTT publisher service for schedule synchronization.

    Responsibilities:
    - Publish schedule create/update messages to ESP32
    - Publish schedule clear messages to ESP32
    - Keep topic naming isolated from motor command topics
    - Provide thread-safe lifecycle and publish operations
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

    def _schedule_set_topic(self, device_id: str) -> str:
        """
        Build MQTT topic for setting or updating a device schedule.
        """
        return f"{self.topic_prefix}/{device_id}/schedule/set"

    def _schedule_clear_topic(self, device_id: str) -> str:
        """
        Build MQTT topic for clearing a device schedule.
        """
        return f"{self.topic_prefix}/{device_id}/schedule/clear"

    def _publish(self, topic: str, payload: dict) -> None:
        """
        Internal helper to publish a JSON payload to MQTT broker.

        Raises:
            AppException: If publish fails.
        """
        client = mqtt.Client(client_id="smartwell-schedule-publisher", clean_session=True)

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
                    "MQTT schedule publish failed: topic=%s, rc=%s",
                    topic,
                    result.rc,
                )
                raise AppException(
                    status_code=502,
                    detail="Failed to publish schedule message to device",
                )

            logger.info(
                "MQTT schedule publish succeeded: topic=%s",
                topic,
            )

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected MQTT schedule publish error: topic=%s, error=%s",
                topic,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=502,
                detail="Unable to communicate schedule update to device",
            )

        finally:
            try:
                client.disconnect()
            except Exception:
                pass

    def publish_schedule_set(
        self,
        device_id: str,
        schedule_type: str,
        pattern: dict,
        schedule_name: str | None,
        is_active: bool = True,
    ) -> None:
        """
        Publish schedule create or update event to a specific device.
        """
        topic = self._schedule_set_topic(device_id)
        payload = {
            "device_id": device_id,
            "command": "SET_SCHEDULE",
            "schedule_type": schedule_type,
            "pattern": pattern,
            "schedule_name": schedule_name,
            "is_active": is_active,
        }

        with self._lock:
            self._publish(topic, payload)

        logger.info(
            "Schedule sync published: device_id=%s, schedule_type=%s",
            device_id,
            schedule_type,
        )

    def publish_schedule_clear(self, device_id: str) -> None:
        """
        Publish schedule clear event to a specific device.
        """
        topic = self._schedule_clear_topic(device_id)
        payload = {
            "device_id": device_id,
            "command": "CLEAR_SCHEDULE",
        }

        with self._lock:
            self._publish(topic, payload)

        logger.info("Schedule clear published: device_id=%s", device_id)