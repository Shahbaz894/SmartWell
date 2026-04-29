import json
import time
from typing import Callable, Any

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import AppException


class MQTTService:
    """
    MQTT service for SmartWell.

    Responsibilities:
    - Publish commands from FastAPI to ESP32.
    - Subscribe to telemetry topics from ESP32.
    - Decode MQTT payloads.
    - Send decoded telemetry to a callback function.

    MQTT topic design:
    - Commands to ESP32:
        tubewell/{device_uid}/motor

    - Telemetry from ESP32:
        tubewell/{device_uid}/telemetry
    """

    def __init__(self):
        self.broker = settings.MQTT_BROKER
        self.port = int(settings.MQTT_PORT)
        self.keepalive = int(settings.MQTT_KEEPALIVE)
        self.topic_prefix = settings.MQTT_COMMAND_TOPIC_PREFIX

    def command_topic(self, device_uid: str) -> str:
        return f"{self.topic_prefix}/{device_uid}/motor"

    def telemetry_topic_all(self) -> str:
        return f"{self.topic_prefix}/+/telemetry"

    def publish_command(self, device_uid: str, payload: dict[str, Any]) -> None:
        """
        Publish command to one ESP32 device.

        Args:
            device_uid: Device UID, for example TB-DEV-001.
            payload: Command JSON payload.

        Raises:
            AppException: If MQTT broker is unreachable or publish fails.
        """
        topic = self.command_topic(device_uid)
        client_id = f"smartwell-publisher-{int(time.time())}"

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=True,
        )

        try:
            logger.info(
                "MQTT publish connecting: broker=%s port=%s topic=%s payload=%s",
                self.broker,
                self.port,
                topic,
                payload,
            )

            client.connect(self.broker, self.port, self.keepalive)
            client.loop_start()

            result = client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=1,
                retain=False,
            )

            result.wait_for_publish(timeout=5)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise AppException(
                    status_code=502,
                    detail=f"MQTT publish failed. topic={topic}, rc={result.rc}",
                )

            logger.info(
                "MQTT publish success: topic=%s payload=%s",
                topic,
                payload,
            )

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "MQTT publish error: broker=%s port=%s topic=%s error_type=%s error=%s",
                self.broker,
                self.port,
                topic,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=502,
                detail=f"MQTT publish error: {type(exc).__name__}: {str(exc)}",
            )

        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    def start_telemetry_subscriber(
        self,
        on_telemetry: Callable[[str, dict[str, Any]], None],
    ) -> mqtt.Client:
        """
        Start MQTT subscriber for ESP32 telemetry.

        Args:
            on_telemetry:
                Callback function.
                It receives:
                    device_uid from topic
                    decoded telemetry payload

        Returns:
            Running MQTT client.

        Example topic:
            tubewell/TB-DEV-001/telemetry

        Example payload:
            {
                "freq": 50.0,
                "current": 10.5,
                "voltage": 220,
                "dcbus": 310,
                "power": 2.1,
                "energy_in": 55.7,
                "fault": false,
                "fault_code": 0,
                "status_code": 1,
                "reference_freq": 50.0,
                "motor_speed": 1450,
                "power_percent": 80,
                "torque_percent": 45,
                "is_live": true
            }
        """
        topic = self.telemetry_topic_all()
        client_id = f"smartwell-telemetry-subscriber-{int(time.time())}"

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=True,
        )

        def on_connect(client, userdata, flags, reason_code, properties):
            if int(reason_code) == 0:
                logger.info(
                    "MQTT telemetry subscriber connected: broker=%s port=%s topic=%s",
                    self.broker,
                    self.port,
                    topic,
                )
                client.subscribe(topic, qos=1)
            else:
                logger.error(
                    "MQTT telemetry subscriber connection failed: reason_code=%s",
                    reason_code,
                )

        def on_message(client, userdata, msg):
            try:
                raw_payload = msg.payload.decode("utf-8")
                parts = msg.topic.split("/")

                if len(parts) != 3:
                    logger.error(
                        "Invalid MQTT telemetry topic: topic=%s payload=%s",
                        msg.topic,
                        raw_payload,
                    )
                    return

                device_uid = parts[1]
                payload = json.loads(raw_payload)

                logger.info(
                    "MQTT telemetry received: topic=%s device_uid=%s payload=%s",
                    msg.topic,
                    device_uid,
                    payload,
                )

                on_telemetry(device_uid, payload)

            except json.JSONDecodeError as exc:
                logger.error(
                    "Invalid MQTT telemetry JSON: topic=%s payload=%s error=%s",
                    msg.topic,
                    msg.payload,
                    str(exc),
                    exc_info=True,
                )

            except Exception as exc:
                logger.error(
                    "MQTT telemetry processing error: topic=%s error_type=%s error=%s",
                    msg.topic,
                    type(exc).__name__,
                    str(exc),
                    exc_info=True,
                )

        client.on_connect = on_connect
        client.on_message = on_message

        try:
            logger.info(
                "Starting MQTT telemetry subscriber: broker=%s port=%s topic=%s",
                self.broker,
                self.port,
                topic,
            )

            client.connect(self.broker, self.port, self.keepalive)
            client.loop_start()

            return client

        except Exception as exc:
            logger.error(
                "Failed to start MQTT telemetry subscriber: broker=%s port=%s error_type=%s error=%s",
                self.broker,
                self.port,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=502,
                detail=f"Failed to start MQTT subscriber: {type(exc).__name__}: {str(exc)}",
            )