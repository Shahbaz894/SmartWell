from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):

    # ─────────────────────────────
    # DATABASE
    # ─────────────────────────────
    DATABASE_URL: str

    # ─────────────────────────────
    # JWT
    # ─────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ─────────────────────────────
    # PROJECT
    # ─────────────────────────────
    PROJECT_NAME: str = "SmartWell API"

    # ─────────────────────────────
    # MQTT
    # ─────────────────────────────
    # ─────────────────────────────
# MQTT
# ─────────────────────────────
    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 1883

    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""

    MQTT_KEEPALIVE: int = 60
    MQTT_QOS: int = 1

    MQTT_COMMAND_TOPIC_PREFIX: str = "tubewell"
    MQTT_TELEMETRY_TOPIC_SUFFIX: str = "telemetry"

    MQTT_CLIENT_ID: str = "smartwell-backend"
    # MQTT_BROKER_HOST: str = "mosquitto"
    # MQTT_BROKER_PORT: int = 1883

    # MQTT_USERNAME: str = ""
    # MQTT_PASSWORD: str = ""

    # MQTT_KEEPALIVE: int = 60
    # MQTT_QOS: int = 1

    # MQTT_COMMAND_TOPIC_PREFIX: str = "tubewell"

    # MQTT_TELEMETRY_TOPIC_PREFIX: str = "smartwell/devices"
    # MQTT_TELEMETRY_TOPIC_SUFFIX: str = "telemetry"

    # MQTT_CLIENT_ID: str = "smartwell-backend"

    # ─────────────────────────────
    # OPTIONAL HTTP
    # ─────────────────────────────
    DEVICE_HTTP_URL: str = ""

    # ─────────────────────────────
    # FIX POSTGRES URL
    # ─────────────────────────────
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres(cls, v: str):
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # ─────────────────────────────
    # ENV CONFIG
    # ─────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()