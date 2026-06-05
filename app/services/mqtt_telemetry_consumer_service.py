# import json
# import re
# import threading
# from typing import Optional

# import paho.mqtt.client as mqtt
# from sqlalchemy.orm import Session

# from app.core.config import settings
# from app.core.logger import logger
# from app.db.session import SessionLocal
# from app.schemas.motor_telemetry_schema import MotorTelemetryCreate
# from app.services.motor_telemetry_service import MotorTelemetryService


# class MQTTTelemetryConsumerService:
#     """
#     MQTT consumer for ESP32 telemetry:
#     topic: tubewell/{device_id}/telemetry
#     """

#     def __init__(self):
#         # CONFIG
#         self.host = settings.MQTT_BROKER
#         self.port = int(settings.MQTT_PORT)
#         self.keepalive = int(settings.MQTT_KEEPALIVE)

#         self.username = settings.MQTT_USERNAME
#         self.password = settings.MQTT_PASSWORD

#         self.topic_prefix = settings.MQTT_COMMAND_TOPIC_PREFIX.strip("/")
#         self.topic_suffix = settings.MQTT_TELEMETRY_TOPIC_SUFFIX.strip("/")
#         self.qos = int(settings.MQTT_QOS)

#         self.service = MotorTelemetryService()

#         self._lock = threading.Lock()
#         self._started = False
#         self._stopping = False

#         # MQTT CLIENT (Paho v2)
#         self.client = mqtt.Client(
#             mqtt.CallbackAPIVersion.VERSION2,
#             client_id="smartwell-telemetry-consumer",
#             clean_session=True,
#         )

#         if self.username:
#             self.client.username_pw_set(self.username, self.password)

#         self.client.reconnect_delay_set(min_delay=1, max_delay=30)

#         # CALLBACKS
#         self.client.on_connect = self.on_connect
#         self.client.on_message = self.on_message
#         self.client.on_disconnect = self.on_disconnect
#         self.client.on_subscribe = self.on_subscribe

#     # -----------------------------
#     # TOPIC HANDLING
#     # -----------------------------
#     # def _telemetry_topic(self) -> str:
#     #     # FIXED (no space bug)
#     #     return f"{self.topic_prefix}/+/{self.topic_suffix}"

#     # def _extract_device_id(self, topic: str) -> Optional[str]:
#     #     pattern = rf"^{re.escape(self.topic_prefix)}/([^/]+)/{re.escape(self.topic_suffix)}$"
#     #     match = re.match(pattern, topic)
#     #     return match.group(1) if match else None
    
#     # -----------------------------
#     # TOPIC HANDLING (UPDATED)
#     # -----------------------------
#     def _telemetry_topic(self) -> str:
#         # Explicitly target 'tubewell' for structural telemetry incoming data streams
#         return "tubewell/+/telemetry"

#     def _extract_device_id(self, topic: str) -> Optional[str]:
#         # Cleanly extract whatever string sits between 'tubewell/' and '/telemetry'
#         pattern = r"^tubewell/([^/]+)/telemetry$"
#         match = re.match(pattern, topic)
#         return match.group(1) if match else None

#     # -----------------------------
#     # MQTT CALLBACKS
#     # -----------------------------
#     def on_connect(self, client, userdata, flags, reason_code, properties=None):
#         if reason_code == 0:
#             topic = self._telemetry_topic()

#             client.subscribe(topic, qos=self.qos)

#             logger.info(
#                 "MQTT connected -> %s:%s | subscribed: %s",
#                 self.host,
#                 self.port,
#                 topic,
#             )
#         else:
#             logger.error("MQTT connection failed: %s", reason_code)

#     def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
#         logger.info("MQTT subscription confirmed mid=%s qos=%s", mid, granted_qos)

#     def on_disconnect(
#         self,
#         client,
#         userdata,
#         disconnect_flags,
#         reason_code,
#         properties=None,
#     ):
#         if self._stopping:
#             logger.info("MQTT disconnected (clean shutdown)")
#             return

#         logger.warning(
#             "MQTT disconnected unexpectedly (reason=%s)",
#             reason_code,
#         )

#     # -----------------------------
#     # MAIN MESSAGE HANDLER
#     # -----------------------------
#     def on_message(self, client, userdata, msg):
#         db: Optional[Session] = None

#         try:
#             topic = msg.topic
#             payload_raw = msg.payload.decode("utf-8").strip()

#             if not payload_raw:
#                 logger.warning("Empty MQTT payload: %s", topic)
#                 return

#             device_id = self._extract_device_id(topic)

#             if not device_id:
#                 logger.warning("Invalid topic ignored: %s", topic)
#                 return

#             payload = json.loads(payload_raw)

#             telemetry = MotorTelemetryCreate(**payload)

#             db = SessionLocal()

#             created = self.service.create_telemetry(
#                 db=db,
#                 device_id=device_id,
#                 data=telemetry,
#             )

#             db.commit()

#             logger.info(
#                 "Telemetry saved -> device=%s id=%s",
#                 device_id,
#                 created.id,
#             )

#         except json.JSONDecodeError as exc:
#             logger.error("JSON decode error: %s", exc)

#         except Exception as exc:
#             if db:
#                 db.rollback()

#             logger.error(
#                 "MQTT processing error: %s",
#                 exc,
#                 exc_info=True,
#             )

#         finally:
#             if db:
#                 db.close()

#     # -----------------------------
#     # START / STOP
#     # -----------------------------
#     def start(self):
#         with self._lock:
#             if self._started:
#                 return

#             try:
#                 logger.info(
#                     "Starting MQTT -> %s:%s",
#                     self.host,
#                     self.port,
#                 )

#                 self.client.connect(
#                     self.host,
#                     self.port,
#                     self.keepalive,
#                 )

#                 self.client.loop_start()

#                 self._started = True
#                 self._stopping = False

#                 logger.info("MQTT consumer started")

#             except Exception as exc:
#                 logger.error("MQTT start failed: %s", exc, exc_info=True)
#                 raise

#     def stop(self):
#         with self._lock:
#             if not self._started:
#                 return

#             self._stopping = True

#             try:
#                 self.client.disconnect()
#                 self.client.loop_stop()

#                 self._started = False

#                 logger.info("MQTT consumer stopped")

#             except Exception as exc:
#                 logger.error("MQTT stop error: %s", exc, exc_info=True)
import json
import re
import threading
from typing import Optional

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import logger
from app.db.session import SessionLocal
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate
from app.services.motor_telemetry_service import MotorTelemetryService


class MQTTTelemetryConsumerService:
    """
    Ecosystem Background Consumer Engine
    Listens to live telemetry at: tubewell/{device_id}/telemetry
    """

    def __init__(self):
        self.host = settings.MQTT_BROKER
        self.port = int(settings.MQTT_PORT)
        self.keepalive = int(settings.MQTT_KEEPALIVE)

        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD

        self.qos = int(settings.MQTT_QOS)
        self.service = MotorTelemetryService()

        self._lock = threading.Lock()
        self._started = False
        self._stopping = False

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="smartwell-telemetry-consumer",
            clean_session=True,
        )

        if self.username:
            self.client.username_pw_set(self.username, self.password)

        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        # Event Handlers Bindings
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe

    def _telemetry_topic(self) -> str:
        return "tubewell/+/telemetry"

    def _extract_device_id(self, topic: str) -> Optional[str]:
        pattern = r"^tubewell/([^/]+)/telemetry$"
        match = re.match(pattern, topic)
        return match.group(1) if match else None

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            topic = self._telemetry_topic()
            client.subscribe(topic, qos=self.qos)
            logger.info(f"📡 Consumer connected to Broker -> Subscribed to: {topic}")
        else:
            logger.error(f"Telemetry subscription connection refused: reason={reason_code}")

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        logger.info(f"Subscription handshake confirmed globally for mid={mid}")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        if self._stopping:
            logger.info("Graceful pipeline shutdown completed for telemetry client.")
            return
        logger.warning(f"Telemetry consumer disconnected unexpectedly! (reason_code={reason_code}). Reconnecting...")

    def on_message(self, client, userdata, msg):
        db: Optional[Session] = None
        try:
            topic = msg.topic
            payload_raw = msg.payload.decode("utf-8").strip()

            if not payload_raw:
                return

            device_id = self._extract_device_id(topic)
            if not device_id:
                logger.warning(f"Discarding rogue topic frame packet: {topic}")
                return

            payload = json.loads(payload_raw)
            telemetry = MotorTelemetryCreate(**payload)

            # Isolated transactional db container pool scope allocation
            db = SessionLocal()
            created = self.service.create_telemetry(
                db=db,
                device_id=device_id,
                data=telemetry,
            )
            db.commit()
            logger.info(f"💾 Telemetry logged safely to DB for device {device_id} (Log ID: {created.id})")

        except json.JSONDecodeError:
            logger.error(f"Malformed JSON schema rejected from topic target stream: {topic}")
        except Exception as exc:
            if db:
                db.rollback()
            logger.error(f"Pipeline processing failure inside engine runtime: {str(exc)}", exc_info=True)
        finally:
            if db:
                db.close()

    def start(self):
        with self._lock:
            if self._started:
                return
            try:
                self.client.connect(self.host, self.port, self.keepalive)
                self.client.loop_start()
                self._started = True
                self._stopping = False
                logger.info("⚡ Background Telemetry Consumer Process Thread Spawned.")
            except Exception as exc:
                logger.error(f"Consumer failure during execution initialization boot: {exc}")
                raise

    def stop(self):
        with self._lock:
            if not self._started:
                return
            self._stopping = True
            try:
                self.client.disconnect()
                self.client.loop_stop()
                self._started = False
                logger.info("🛑 Background Telemetry Consumer safely powered down.")
            except Exception as exc:
                logger.error(f"Error stopping network loops safely: {exc}")