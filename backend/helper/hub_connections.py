import json
import logging
import threading
from typing import Any, Dict, Literal, Optional

from jhomeassistant import HomeAssistantConnection
from jmqtt import MQTTBuilderV3, MQTTConnectionV3, QualityOfService as QoS

from database.schemas.settings import Settings
from helper.settings_cipher import SettingsCipher


HubRole = Literal["hub", "agent"]


class HubConnections:
    DEFAULT_TOPIC_PREFIX = "ir-hub"
    DEFAULT_APP_NAME = "ir-hub"

    def __init__(
        self,
        settings_store: Settings,
        settings_cipher: SettingsCipher,
        role: HubRole,
        homeassistant_origin_name: str = "IR Hub",
        enable_homeassistant: bool = True,
    ) -> None:
        self._settings_store = settings_store
        self._settings_cipher = settings_cipher
        self._role = role
        self._homeassistant_origin_name = homeassistant_origin_name
        self._homeassistant_enabled = bool(enable_homeassistant) and role == "hub"

        self._logger = logging.getLogger("hub_connections")
        self._lock = threading.Lock()

        self._mqtt_connection: Optional[MQTTConnectionV3] = None
        self._ha_connection: Optional[HomeAssistantConnection] = None
        self._ha_thread: Optional[threading.Thread] = None
        self._last_error: Optional[str] = None

        self._active_config: Optional[Dict[str, Any]] = None

    def start(self) -> None:
        self.reload()

    def stop(self) -> None:
        self._last_error = None
        self._active_config = None
        self._close_connection()

    def reload(self) -> None:
        try:
            runtime = self._load_runtime_settings()
            next_config = self._build_connection_config(runtime)
            if not next_config["host"]:
                self._last_error = None
                self._active_config = None
                self._close_connection()
                return

            with self._lock:
                unchanged = next_config == self._active_config
                has_connection = self._mqtt_connection is not None
            if unchanged and has_connection:
                return

            self._close_connection()
            self._active_config = next_config
            self._connect(next_config)
            self._last_error = None
        except Exception as exc:
            self._logger.warning(f"MQTT initialization failed: {exc}")
            self._last_error = str(exc)
            self._active_config = None
            self._close_connection()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            connection = self._mqtt_connection
            config = dict(self._active_config) if self._active_config else None
            ha_thread = self._ha_thread
            connected = self._is_connected(connection)
            ha_thread_running = ha_thread is not None and ha_thread.is_alive()

        app_name = config["app_name"] if config else self.DEFAULT_APP_NAME
        instance = config["instance"] if config else ""
        base_topic = config["base_topic"] if config else self._default_base_topic()

        return {
            "configured": config is not None,
            "connected": connected,
            "role": self._role,
            "instance": instance,
            "base_topic": base_topic,
            "app_name": app_name,
            "client_id_prefix": app_name,
            "homeassistant_enabled": self._homeassistant_enabled,
            "homeassistant_thread_running": ha_thread_running,
            "last_error": self._last_error,
        }

    def homeassistant_connection(self) -> Optional[HomeAssistantConnection]:
        with self._lock:
            return self._ha_connection

    def start_homeassistant_thread(
        self,
        schedule_resolution: float = 1.0,
        publish_timeout: Optional[float] = None,
    ) -> None:
        with self._lock:
            if not self._homeassistant_enabled:
                return
            ha_connection = self._ha_connection
            if ha_connection is None:
                return

            existing = self._ha_thread
            if existing is not None and existing.is_alive():
                return
            if existing is not None and not existing.is_alive():
                self._ha_thread = None

            thread = threading.Thread(
                target=self._homeassistant_thread_main,
                args=(ha_connection, schedule_resolution, publish_timeout),
                daemon=True,
                name="homeassistant_runtime",
            )
            self._ha_thread = thread
        thread.start()

    def topic(self, relative_topic: str) -> str:
        relative = self._normalize_topic_part(relative_topic)
        with self._lock:
            base_topic = self._active_config["base_topic"] if self._active_config else self._default_base_topic()
        if not relative:
            return base_topic
        return f"{base_topic}/{relative}"

    def publish(
        self,
        relative_topic: str,
        payload: Any,
        qos: QoS = QoS.AtLeastOnce,
        retain: bool = False,
        wait_for_publish: bool = False,
    ):
        topic = self.topic(relative_topic)
        with self._lock:
            connection = self._mqtt_connection
            connected = self._is_connected(connection)
        if connection is None or not connected:
            raise RuntimeError("mqtt_not_connected")
        return connection.publish(topic, payload, qos=qos, retain=retain, wait_for_publish=wait_for_publish)

    def publish_json(
        self,
        relative_topic: str,
        payload: Dict[str, Any],
        qos: QoS = QoS.AtLeastOnce,
        retain: bool = False,
        wait_for_publish: bool = False,
    ):
        message = json.dumps(payload, separators=(",", ":"))
        return self.publish(
            relative_topic=relative_topic,
            payload=message,
            qos=qos,
            retain=retain,
            wait_for_publish=wait_for_publish,
        )

    def _load_runtime_settings(self) -> Dict[str, Any]:
        return self._settings_store.get_mqtt_runtime_settings(settings_cipher=self._settings_cipher)

    def _build_connection_config(self, runtime: Dict[str, Any]) -> Dict[str, Any]:
        host = str(runtime.get("mqtt_host") or "").strip()
        port = int(runtime.get("mqtt_port") or 1883)
        username = str(runtime.get("mqtt_username") or "").strip()
        password = str(runtime.get("mqtt_password") or "")

        instance_raw = str(runtime.get("mqtt_instance") or "")
        instance = self._normalize_topic_part(instance_raw)

        app_name = str(runtime.get("mqtt_client_id_prefix") or self.DEFAULT_APP_NAME).strip() or self.DEFAULT_APP_NAME
        base_topic = self._base_topic_for_instance(instance)

        return {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "instance": instance,
            "base_topic": base_topic,
            "app_name": app_name,
            "role": self._role,
        }

    def _connect(self, config: Dict[str, Any]) -> None:
        builder = MQTTBuilderV3(host=config["host"], app_name=config["app_name"])
        if config["instance"]:
            builder.instance_id(config["instance"])

        builder.port(config["port"])
        builder.keep_alive(60)
        builder.auto_reconnect(min_delay=1, max_delay=30)

        if config["username"]:
            builder.login(config["username"], config["password"])

        builder.availability(
            topic=self._availability_topic(config)
        )

        connection = builder.build()

        ha_connection = None
        if self._homeassistant_enabled:
            ha_connection = HomeAssistantConnection(connection)
            ha_connection.origin.name = self._homeassistant_origin_name

        with self._lock:
            self._mqtt_connection = connection
            self._ha_connection = ha_connection

        connection.connect()

    def _close_connection(self) -> None:
        with self._lock:
            connection = self._mqtt_connection
            self._mqtt_connection = None
            self._ha_connection = None
        if connection is None:
            return
        try:
            connection.close()
        except Exception as exc:
            self._logger.warning(f"Failed to close MQTT connection cleanly: {exc}")

    def _homeassistant_thread_main(
        self,
        ha_connection: HomeAssistantConnection,
        schedule_resolution: float,
        publish_timeout: Optional[float],
    ) -> None:
        try:
            ha_connection.run(schedule_resolution=schedule_resolution, publish_timeout=publish_timeout)
        except Exception as exc:
            self._logger.warning(f"Home Assistant runtime stopped: {exc}")
        finally:
            with self._lock:
                if threading.current_thread() is self._ha_thread:
                    self._ha_thread = None

    def _availability_topic(self, config: Dict[str, Any]) -> str:
        return f"{config['base_topic']}/{config['role']}/status"

    def _base_topic_for_instance(self, instance: str) -> str:
        normalized_instance = self._normalize_topic_part(instance)
        if not normalized_instance:
            return self.DEFAULT_TOPIC_PREFIX
        return f"{self.DEFAULT_TOPIC_PREFIX}/{normalized_instance}"

    def _default_base_topic(self) -> str:
        return self.DEFAULT_TOPIC_PREFIX

    def _normalize_topic_part(self, value: str) -> str:
        return str(value or "").strip().strip("/")

    def _is_connected(self, connection: Optional[MQTTConnectionV3]) -> bool:
        return connection is not None and bool(connection.is_connected)
