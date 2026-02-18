import json
import logging
import threading
from typing import Any, Dict, Optional

from jmqtt import MQTTBuilderV3, MQTTConnectionV3, QualityOfService as QoS

from .mqtt_connection_model import MQTTConnectionModel, ConnectionRole


class MqttHandler:
    def __init__(self, role: ConnectionRole) -> None:
        self._role = role
        self._lock = threading.Lock()
        self._logger = logging.getLogger("mqtt_handler")
        self._connection: Optional[MQTTConnectionV3] = None
        self._active_model: Optional[MQTTConnectionModel] = None
        self._last_error: Optional[str] = None

    @property
    def technical_name(self) -> str:
        return f"ir-{self._role}"

    @property
    def readable_name(self) -> str:
        return "IR Hub" if self._role == "hub" else "IR Agent"

    def start(self, model: MQTTConnectionModel) -> None:
        if not model.is_mqtt_configured:
            self.stop()
            with self._lock:
                self._active_model = model
                self._last_error = None
            return

        with self._lock:
            current_model = self._active_model
            current_connection = self._connection
            already_connected = self._is_connected(current_connection)
            unchanged = current_model == model and already_connected
        if unchanged:
            return

        self.stop()
        try:
            connection = self._connect(model)
            with self._lock:
                self._connection = connection
                self._active_model = model
                self._last_error = None
        except Exception as exc:
            with self._lock:
                self._active_model = model
                self._last_error = str(exc)
            self._logger.warning(f"MQTT start failed: {exc}")
            raise

    def stop(self) -> None:
        with self._lock:
            connection = self._connection
            self._connection = None
        if connection is None:
            return
        try:
            connection.close()
        except Exception as exc:
            self._logger.warning(f"Failed to close MQTT connection cleanly: {exc}")

    def reload(self, model: MQTTConnectionModel) -> None:
        self.start(model)

    def mark_error(self, message: str) -> None:
        with self._lock:
            self._last_error = str(message)
            if self._active_model is None:
                self._active_model = MQTTConnectionModel(
                    role=self._role,
                    host="",
                    port=1883,
                    username="",
                    password="",
                    instance="",
                    readable_name=self.readable_name,
                )

    def status(self) -> Dict[str, Any]:
        with self._lock:
            model = self._active_model
            connection = self._connection
            last_error = self._last_error

        if model is None:
            base_topic = self.technical_name
            instance = ""
            app_name = self.technical_name
            configured = False
        else:
            base_topic = model.base_topic
            instance = model.instance
            app_name = model.app_name
            configured = model.is_mqtt_configured

        return {
            "configured": configured,
            "connected": self._is_connected(connection),
            "role": self._role,
            "instance": instance,
            "base_topic": base_topic,
            "app_name": app_name,
            "last_error": last_error,
        }

    def connection(self) -> Optional[MQTTConnectionV3]:
        with self._lock:
            return self._connection

    def topic(self, relative_topic: str) -> str:
        relative = self._normalize_topic_part(relative_topic)
        with self._lock:
            model = self._active_model
        base_topic = model.base_topic if model is not None else self.technical_name
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
            connection = self._connection
        if connection is None or not self._is_connected(connection):
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
        text = json.dumps(payload, separators=(",", ":"))
        return self.publish(
            relative_topic=relative_topic,
            payload=text,
            qos=qos,
            retain=retain,
            wait_for_publish=wait_for_publish,
        )

    def _connect(self, model: MQTTConnectionModel) -> MQTTConnectionV3:
        builder = MQTTBuilderV3(host=model.host, app_name=model.app_name)
        if model.instance:
            builder.instance_id(model.instance)
        builder.port(model.port)
        builder.keep_alive(60)
        builder.auto_reconnect(min_delay=1, max_delay=30)
        if model.username:
            builder.login(model.username, model.password)
        builder.availability(topic=model.availability_topic)
        connection = builder.build()
        connection.connect()
        return connection

    def _is_connected(self, connection: Optional[MQTTConnectionV3]) -> bool:
        return connection is not None and bool(connection.is_connected)

    def _normalize_topic_part(self, value: str) -> str:
        return str(value or "").strip().strip("/")
