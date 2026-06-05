# # import json
# # import time
# # from typing import Callable, Any

# # import paho.mqtt.client as mqtt

# # from app.core.config import settings
# # from app.core.logger import logger
# # from app.core.exceptions import AppException


# # class MQTTService:
# #     """
# #     MQTT service for SmartWell.

# #     Responsibilities:
# #     - Publish commands from FastAPI to ESP32.
# #     - Subscribe to telemetry topics from ESP32.
# #     - Decode MQTT payloads.
# #     - Send decoded telemetry to a callback function.

# #     MQTT topic design:
# #     - Commands to ESP32:
# #         tubewell/{device_uid}/motor

# #     - Telemetry from ESP32:
# #         tubewell/{device_uid}/telemetry
# #     """

# #     def __init__(self):
# #         self.broker = settings.MQTT_BROKER
# #         self.port = int(settings.MQTT_PORT)
# #         self.keepalive = int(settings.MQTT_KEEPALIVE)
# #         self.topic_prefix = settings.MQTT_COMMAND_TOPIC_PREFIX

# #     def command_topic(self, device_uid: str) -> str:
# #         return f"{self.topic_prefix}/{device_uid}/motor"

# #     def telemetry_topic_all(self) -> str:
# #         return f"{self.topic_prefix}/+/telemetry"

# #     # 🔥 FIX: Added Class Method to handle direct routing from MotorTimerService
# #     @classmethod
# #     def publish_motor_command(cls, device_uid: str, action: str) -> None:
# #         """
# #         Class method used by MotorTimerService to turn a motor ON or OFF.
# #         Converts the action string into the explicit schema dictionary payload.
# #         """
# #         instance = cls()
# #         # Build the exact key-value structural map your hardware microcontrollers read
# #         payload = {"action": action.upper()} 
        
# #         logger.info(f"Routing timer command via class method: device={device_uid}, payload={payload}")
# #         instance.publish_command(device_uid=device_uid, payload=payload)

# #     def publish_command(self, device_uid: str, payload: dict[str, Any]) -> None:
# #         """
# #         Publish command to one ESP32 device.

# #         Args:
# #             device_uid: Device UID, for example TB-DEV-001.
# #             payload: Command JSON payload.

# #         Raises:
# #             AppException: If MQTT broker is unreachable or publish fails.
# #         """
# #         topic = self.command_topic(device_uid)
# #         client_id = f"smartwell-publisher-{int(time.time())}"

# #         client = mqtt.Client(
# #             mqtt.CallbackAPIVersion.VERSION2,
# #             client_id=client_id,
# #             clean_session=True,
# #         )

# #         try:
# #             logger.info(
# #                 "MQTT publish connecting: broker=%s port=%s topic=%s payload=%s",
# #                 self.broker,
# #                 self.port,
# #                 topic,
# #                 payload,
# #             )

# #             client.connect(self.broker, self.port, self.keepalive)
# #             client.loop_start()

# #             result = client.publish(
# #                 topic=topic,
# #                 payload=json.dumps(payload),
# #                 qos=1,
# #                 retain=False,
# #             )

# #             result.wait_for_publish(timeout=5)

# #             if result.rc != mqtt.MQTT_ERR_SUCCESS:
# #                 raise AppException(
# #                     status_code=502,
# #                     detail=f"MQTT publish failed. topic={topic}, rc={result.rc}",
# #                 )

# #             logger.info(
# #                 "MQTT publish success: topic=%s payload=%s",
# #                 topic,
# #                 payload,
# #             )

# #         except AppException:
# #             raise

# #         except Exception as exc:
# #             logger.error(
# #                 "MQTT publish error: broker=%s port=%s topic=%s error_type=%s error=%s",
# #                 self.broker,
# #                 self.port,
# #                 topic,
# #                 type(exc).__name__,
# #                 str(exc),
# #                 exc_info=True,
# #             )
# #             raise AppException(
# #                 status_code=502,
# #                 detail=f"MQTT publish error: {type(exc).__name__}: {str(exc)}",
# #             )

# #         finally:
# #             try:
# #                 client.loop_stop()
# #                 client.disconnect()
# #             except Exception:
# #                 pass

# #     def start_telemetry_subscriber(
# #         self,
# #         on_telemetry: Callable[[str, dict[str, Any]], None],
# #     ) -> mqtt.Client:
# #         """
# #         Start MQTT subscriber for ESP32 telemetry.
# #         """
# #         topic = self.telemetry_topic_all()
# #         client_id = f"smartwell-telemetry-subscriber-{int(time.time())}"

# #         client = mqtt.Client(
# #             mqtt.CallbackAPIVersion.VERSION2,
# #             client_id=client_id,
# #             clean_session=True,
# #         )

# #         def on_connect(client, userdata, flags, reason_code, properties):
# #             if int(reason_code) == 0:
# #                 logger.info(
# #                     "MQTT telemetry subscriber connected: broker=%s port=%s topic=%s",
# #                     self.broker,
# #                     self.port,
# #                     topic,
# #                 )
# #                 client.subscribe(topic, qos=1)
# #             else:
# #                 logger.error(
# #                     "MQTT telemetry subscriber connection failed: reason_code=%s",
# #                     reason_code,
# #                 )

# #         def on_message(client, userdata, msg):
# #             try:
# #                 raw_payload = msg.payload.decode("utf-8")
# #                 parts = msg.topic.split("/")

# #                 if len(parts) != 3:
# #                     logger.error(
# #                         "Invalid MQTT telemetry topic: topic=%s payload=%s",
# #                         msg.topic,
# #                         raw_payload,
# #                     )
# #                     return

# #                 device_uid = parts[1]
# #                 payload = json.loads(raw_payload)

# #                 logger.info(
# #                     "MQTT telemetry received: topic=%s device_uid=%s payload=%s",
# #                     msg.topic,
# #                     device_uid,
# #                     payload,
# #                 )

# #                 on_telemetry(device_uid, payload)

# #             except json.JSONDecodeError as exc:
# #                 logger.error(
# #                     "Invalid MQTT telemetry JSON: topic=%s payload=%s error=%s",
# #                     msg.topic,
# #                     msg.payload,
# #                     str(exc),
# #                     exc_info=True,
# #                 )

# #             except Exception as exc:
# #                 logger.error(
# #                     "MQTT telemetry processing error: topic=%s error_type=%s error=%s",
# #                     msg.topic,
# #                     type(exc).__name__,
# #                     str(exc),
# #                     exc_info=True,
# #                 )

# #         client.on_connect = on_connect
# #         client.on_message = on_message

# #         try:
# #             logger.info(
# #                 "Starting MQTT telemetry subscriber: broker=%s port=%s topic=%s",
# #                 self.broker,
# #                 self.port,
# #                 topic,
# #             )

# #             client.connect(self.broker, self.port, self.keepalive)
# #             client.loop_start()

# #             return client

# #         except Exception as exc:
# #             logger.error(
# #                 "Failed to start MQTT telemetry subscriber: broker=%s port=%s error_type=%s error=%s",
# #                 self.broker,
# #                 self.port,
# #                 type(exc).__name__,
# #                 str(exc),
# #                 exc_info=True,
# #             )
# #             raise AppException(
# #                 status_code=502,
# #                 detail=f"Failed to start MQTT subscriber: {type(exc).__name__}: {str(exc)}",
# #             )
# import json
# import time
# from typing import Any, Optional
# import paho.mqtt.client as mqtt

# from app.core.config import settings
# from app.core.logger import logger
# from app.core.exceptions import AppException


# class MQTTService:
#     """
#     Thread-safe, Long-lived MQTT service for SmartWell Backend.
#     Reuse status: Single continuous connection for blazing-fast commands.
#     """
#     _instance: Optional['MQTTService'] = None
    
#     def __new__(cls, *args, **kwargs):
#         if not cls._instance:
#             cls._instance = super(MQTTService, cls).__new__(cls, *args, **kwargs)
#             cls._instance._initialized = False
#         return cls._instance

#     def __init__(self):
#         if self._initialized:
#             return
            
#         self.broker = settings.MQTT_BROKER
#         self.port = int(settings.MQTT_PORT)
#         self.keepalive = int(settings.MQTT_KEEPALIVE)
#         self.topic_prefix = settings.MQTT_COMMAND_TOPIC_PREFIX.strip("/")
        
#         # Initialize a single shared client for publishing
#         client_id = f"smartwell-backend-shared-publisher"
#         self.client = mqtt.Client(
#             mqtt.CallbackAPIVersion.VERSION2,
#             client_id=client_id,
#             clean_session=True,
#         )
        
#         if settings.MQTT_USERNAME:
#             self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            
#         self.client.on_disconnect = self._on_disconnect
#         self._connect_and_start()
#         self._initialized = True

#     def _connect_and_start(self):
#         try:
#             logger.info("Initializing persistent MQTT Publisher connection...")
#             self.client.connect(self.broker, self.port, self.keepalive)
#             self.client.loop_start()
#         except Exception as e:
#             logger.error(f"Failed to initialize global MQTT Publisher: {e}")

#     def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
#         logger.warning(f"Shared MQTT Publisher disconnected (rc={reason_code}). Reconnecting...")
#         # Auto-reconnection logic handled by Paho inside loop_start()

#     def command_topic(self, device_uid: str) -> str:
#         return f"{self.topic_prefix}/{device_uid}/motor"

#     @classmethod
#     def publish_motor_command(cls, device_uid: str, action: str) -> None:
#         """
#         Class method for direct routing via Timer or REST API Endpoints.
#         """
#         instance = cls()
#         # ⚡ Standardized schema key: Both fields sent to ensure hardware compatibility
#         payload = {"command": action.upper(), "action": action.upper()} 
#         logger.info(f"Routing command via shared publisher: device={device_uid}, payload={payload}")
#         instance.publish_command(device_uid=device_uid, payload=payload)

#     def publish_command(self, device_uid: str, payload: dict[str, Any]) -> None:
#         """
#         Publishes command over the persistent shared network loop without re-connecting.
#         """
#         topic = self.command_topic(device_uid)

#         try:
#             # Check connection state before firing
#             if not self.client.is_connected():
#                 logger.warning("Shared client disconnected, attempting emergency reconnect...")
#                 self.client.reconnect()

#             result = self.client.publish(
#                 topic=topic,
#                 payload=json.dumps(payload),
#                 qos=1,
#                 retain=False,
#             )
            
#             # Non-blocking check with localized fast timeout
#             rc, _ = result.rc, result.mid
#             if rc != mqtt.MQTT_ERR_SUCCESS:
#                 raise AppException(
#                     status_code=502,
#                     detail=f"MQTT push failed straight from buffer pool. rc={rc}",
#                 )
                
#             logger.info(f"🚀 Command dispatched instantaneously to MQTT topic: {topic}")

#         except Exception as exc:
#             logger.error(f"MQTT async delivery crash: {str(exc)}", exc_info=True)
#             raise AppException(
#                 status_code=502,
#                 detail=f"MQTT delivery ecosystem error: {str(exc)}",
#             )


import json
from typing import Any, Optional
import paho.mqtt.client as mqtt

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import AppException


class MQTTService:
    """
    Thread-safe, Long-lived MQTT service for SmartWell Backend.
    Sirf Outbound Commands handle karta hai (Blazing-fast execution).
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
        
        client_id = "smartwell-backend-shared-publisher"
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=True,
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
        logger.warning(f"Shared MQTT Publisher disconnected (rc={reason_code}). Reconnecting automatically...")

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
            if not self.client.is_connected():
                logger.warning("Shared client disconnected, attempting emergency reconnect...")
                self.client.reconnect()

            result = self.client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=1,
                retain=False,
            )
            
            rc = result.rc
            if rc != mqtt.MQTT_ERR_SUCCESS:
                raise AppException(
                    status_code=502,
                    detail=f"MQTT push failed straight from buffer pool. rc={rc}",
                )
                
            logger.info(f"🚀 Command dispatched instantaneously to MQTT topic: {topic}")

        except Exception as exc:
            logger.error(f"MQTT async delivery crash: {str(exc)}", exc_info=True)
            raise AppException(
                status_code=502,
                detail=f"MQTT delivery ecosystem error: {str(exc)}",
            )