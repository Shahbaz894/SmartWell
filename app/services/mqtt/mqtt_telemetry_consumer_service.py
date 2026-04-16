# import json
# import re
# import threading
# from typing import Optional

# import paho.mqtt.client as mqtt
# from sqlalchemy.orm import Session

# from app.core.config import settings
# from app.core.exceptions import AppException
# from app.core.logger import logger
# from app.db.session import SessionLocal
# from app.schemas.motor_telemetry_schema import MotorTelemetryCreate
# from app.services.motor_telemetry_service import MotorTelemetryService


# class MQTTTelemetryConsumerService:
#     """
#     MQTT consumer service for ESP32 motor telemetry.

#     Responsibilities:
#     - Connect to MQTT broker in background thread mode
#     - Subscribe to telemetry topics for all devices
#     - Parse and validate telemetry payloads
#     - Extract device_id from topic
#     - Persist live and offline telemetry packets into the database
#     - Handle reconnects safely
#     - Support clean startup and shutdown lifecycle

#     Expected topic format:
#         {MQTT_TELEMETRY_TOPIC_PREFIX}/{device_id}/{MQTT_TELEMETRY_TOPIC_SUFFIX}

#     Example:
#         smartwell/devices/device_001/telemetry
#     """

#     def __init__(self):
#         self.host = settings.MQTT_BROKER_HOST
#         self.port = settings.MQTT_BROKER_PORT
#         self.username = settings.MQTT_USERNAME
#         self.password = settings.MQTT_PASSWORD
#         self.keepalive = settings.MQTT_KEEPALIVE
#         self.topic_prefix = settings.MQTT_TELEMETRY_TOPIC_PREFIX
#         self.topic_suffix = settings.MQTT_TELEMETRY_TOPIC_SUFFIX
#         self.qos = settings.MQTT_QOS

#         self.telemetry_service = MotorTelemetryService()

#         self._lock = threading.Lock()
#         self._started = False
#         self._stopping = False

#         client_id = f"smartwell-telemetry-consumer-{self.host}-{self.port}"

#         self.client = mqtt.Client(
#             client_id=client_id,
#             clean_session=True,
#         )

#         if self.username:
#             self.client.username_pw_set(self.username, self.password)

#         # Automatic reconnect backoff
#         self.client.reconnect_delay_set(min_delay=1, max_delay=30)

#         # Callbacks
#         self.client.on_connect = self.on_connect
#         self.client.on_message = self.on_message
#         self.client.on_disconnect = self.on_disconnect
#         self.client.on_subscribe = self.on_subscribe
#         self.client.on_log = self.on_log

#     def _telemetry_wildcard_topic(self) -> str:
#         """
#         Return wildcard topic used to subscribe to all device telemetry topics.
#         """
#         return f"{self.topic_prefix}/+/{self.topic_suffix}"

#     def _extract_device_id_from_topic(self, topic: str) -> Optional[str]:
#         """
#         Extract device_id from telemetry topic.

#         Example:
#             smartwell/devices/device_001/telemetry -> device_001

#         Args:
#             topic: MQTT topic string

#         Returns:
#             Extracted device_id or None if format is invalid
#         """
#         pattern = rf"^{re.escape(self.topic_prefix)}/([^/]+)/{re.escape(self.topic_suffix)}$"
#         match = re.match(pattern, topic)
#         if not match:
#             return None
#         return match.group(1)

#     def on_connect(self, client, userdata, flags, reason_code, properties=None):
#         """
#         MQTT on_connect callback.

#         Subscribes to telemetry wildcard topic after successful connection.
#         """
#         try:
#             if reason_code == 0:
#                 topic = self._telemetry_wildcard_topic()
#                 result, mid = client.subscribe(topic, qos=self.qos)

#                 if result != mqtt.MQTT_ERR_SUCCESS:
#                     logger.error(
#                         "MQTT subscribe failed after connect: host=%s, port=%s, topic=%s, result=%s",
#                         self.host,
#                         self.port,
#                         topic,
#                         result,
#                     )
#                     return

#                 logger.info(
#                     "MQTT telemetry consumer connected successfully: host=%s, port=%s, topic=%s, qos=%s, mid=%s",
#                     self.host,
#                     self.port,
#                     topic,
#                     self.qos,
#                     mid,
#                 )
#             else:
#                 logger.error(
#                     "MQTT telemetry consumer connection rejected: host=%s, port=%s, reason_code=%s",
#                     self.host,
#                     self.port,
#                     reason_code,
#                 )

#         except Exception as exc:
#             logger.error(
#                 "Unexpected error in on_connect callback: error=%s",
#                 exc,
#                 exc_info=True,
#             )

#     def on_disconnect(self, client, userdata, reason_code, properties=None):
#         """
#         MQTT on_disconnect callback.

#         Logs clean or unexpected disconnects. Automatic reconnect is handled
#         by the MQTT client loop when not intentionally stopping.
#         """
#         try:
#             if self._stopping:
#                 logger.info("MQTT telemetry consumer disconnected during shutdown")
#                 return

#             if reason_code != 0:
#                 logger.warning(
#                     "MQTT telemetry consumer disconnected unexpectedly: reason_code=%s. Auto-reconnect remains enabled.",
#                     reason_code,
#                 )
#             else:
#                 logger.info("MQTT telemetry consumer disconnected cleanly")

#         except Exception as exc:
#             logger.error(
#                 "Unexpected error in on_disconnect callback: error=%s",
#                 exc,
#                 exc_info=True,
#             )

#     def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
#         """
#         MQTT on_subscribe callback.
#         """
#         try:
#             logger.info(
#                 "MQTT telemetry subscription confirmed: mid=%s, granted_qos=%s",
#                 mid,
#                 granted_qos,
#             )
#         except Exception as exc:
#             logger.error(
#                 "Unexpected error in on_subscribe callback: error=%s",
#                 exc,
#                 exc_info=True,
#             )

#     def on_log(self, client, userdata, level, buf):
#         """
#         MQTT internal log callback.

#         Only warnings and errors are forwarded to application logs to avoid noise.
#         """
#         try:
#             if level in (mqtt.MQTT_LOG_WARNING, mqtt.MQTT_LOG_ERR):
#                 logger.warning("MQTT internal log: %s", buf)
#         except Exception:
#             pass

#     def on_message(self, client, userdata, msg):
#         """
#         MQTT on_message callback.

#         Handles telemetry packets from ESP32 and persists them safely.

#         Behavior:
#         - Extract device_id from topic
#         - Decode JSON payload
#         - Validate payload using Pydantic schema
#         - Create telemetry row in DB
#         """
#         db: Optional[Session] = None

#         try:
#             topic = msg.topic
#             payload_bytes = msg.payload or b""

#             if not payload_bytes:
#                 logger.warning("Ignoring empty telemetry payload: topic=%s", topic)
#                 return

#             raw_payload = payload_bytes.decode("utf-8").strip()
#             if not raw_payload:
#                 logger.warning("Ignoring blank telemetry payload: topic=%s", topic)
#                 return

#             device_id = self._extract_device_id_from_topic(topic)
#             if not device_id:
#                 logger.warning(
#                     "Ignoring telemetry with invalid topic format: topic=%s",
#                     topic,
#                 )
#                 return

#             payload_dict = json.loads(raw_payload)
#             telemetry_data = MotorTelemetryCreate(**payload_dict)

#             db = SessionLocal()

#             created = self.telemetry_service.create_telemetry(
#                 db=db,
#                 device_id=device_id,
#                 data=telemetry_data,
#             )

#             logger.info(
#                 "Telemetry packet processed successfully: device_id=%s, telemetry_id=%s, is_live=%s",
#                 device_id,
#                 created.id,
#                 created.is_live,
#             )

#         except UnicodeDecodeError as exc:
#             if db:
#                 db.rollback()
#             logger.error(
#                 "Telemetry payload decode error: topic=%s, error=%s",
#                 msg.topic,
#                 exc,
#                 exc_info=True,
#             )

#         except json.JSONDecodeError as exc:
#             if db:
#                 db.rollback()
#             logger.error(
#                 "Invalid JSON telemetry payload: topic=%s, error=%s",
#                 msg.topic,
#                 exc,
#                 exc_info=True,
#             )

#         except AppException as exc:
#             if db:
#                 db.rollback()
#             logger.error(
#                 "Telemetry validation or persistence error: topic=%s, detail=%s",
#                 msg.topic,
#                 getattr(exc, "detail", str(exc)),
#                 exc_info=True,
#             )

#         except Exception as exc:
#             if db:
#                 db.rollback()
#             logger.error(
#                 "Unexpected telemetry consumer error: topic=%s, error=%s",
#                 msg.topic,
#                 exc,
#                 exc_info=True,
#             )

#         finally:
#             if db:
#                 db.close()

#     def start(self):
#         """
#         Start MQTT telemetry consumer in background thread mode.

#         Safe behavior:
#         - Prevents duplicate start calls
#         - Enables auto reconnect
#         - Uses non-blocking async connect
#         """
#         with self._lock:
#             if self._started:
#                 logger.warning("MQTT telemetry consumer start skipped: already running")
#                 return

#             self._stopping = False

#             try:
#                 logger.info(
#                     "Starting MQTT telemetry consumer: host=%s, port=%s, keepalive=%s",
#                     self.host,
#                     self.port,
#                     self.keepalive,
#                 )

#                 self.client.connect_async(self.host, self.port, self.keepalive)
#                 self.client.loop_start()

#                 self._started = True

#                 logger.info("MQTT telemetry consumer background loop started successfully")

#             except Exception as exc:
#                 self._started = False
#                 logger.error(
#                     "Failed to start MQTT telemetry consumer: error=%s",
#                     exc,
#                     exc_info=True,
#                 )
#                 raise AppException(
#                     status_code=500,
#                     detail="Failed to start MQTT telemetry consumer",
#                 )

#     def stop(self):
#         """
#         Stop MQTT telemetry consumer safely.

#         Safe behavior:
#         - Prevents duplicate stop calls
#         - Signals shutdown state before disconnect
#         - Stops network loop cleanly
#         """
#         with self._lock:
#             if not self._started:
#                 logger.info("MQTT telemetry consumer stop skipped: not running")
#                 return

#             self._stopping = True

#             try:
#                 logger.info("Stopping MQTT telemetry consumer")

#                 try:
#                     self.client.disconnect()
#                 finally:
#                     self.client.loop_stop()

#                 self._started = False

#                 logger.info("MQTT telemetry consumer stopped successfully")

#             except Exception as exc:
#                 logger.error(
#                     "Failed to stop MQTT telemetry consumer cleanly: error=%s",
#                     exc,
#                     exc_info=True,
#                 )
#                 self._started = False