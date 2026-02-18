from typing import Any, Dict, Literal

from database.schemas.settings import Settings
from helper.settings_cipher import SettingsCipher

from .homeassistant_connection_model import HomeAssistantConnectionModel
from .homeassistant_handler import HomeAssistantHandler
from .mqtt_connection_model import MQTTConnectionModel
from .mqtt_handler import MqttHandler


ConnectionRole = Literal["hub", "agent"]


class RuntimeLoader:
    def __init__(self, settings_store: Settings, settings_cipher: SettingsCipher, role: ConnectionRole) -> None:
        self._settings_store = settings_store
        self._settings_cipher = settings_cipher
        self._role = role
        self._mqtt_handler = MqttHandler(role=role)
        self._homeassistant_handler = HomeAssistantHandler()

    @property
    def technical_name(self) -> str:
        return self._mqtt_handler.technical_name

    @property
    def readable_name(self) -> str:
        return self._mqtt_handler.readable_name

    def start(self) -> None:
        self.reload()

    def stop(self) -> None:
        self._homeassistant_handler.stop()
        self._mqtt_handler.stop()

    def reload(self) -> None:
        try:
            runtime_settings = self._settings_store.get_runtime_settings(settings_cipher=self._settings_cipher)
            mqtt_model = self._build_mqtt_model(runtime_settings)
            homeassistant_model = self._build_homeassistant_model(runtime_settings)
            self._mqtt_handler.reload(mqtt_model)
            self._homeassistant_handler.configure(homeassistant_model, self._mqtt_handler.connection())
            self._homeassistant_handler.start()
        except Exception as exc:
            self._mqtt_handler.stop()
            self._homeassistant_handler.stop()
            self._mqtt_handler.mark_error(str(exc))

    def status(self) -> Dict[str, Any]:
        mqtt_status = self._mqtt_handler.status()
        mqtt_status.update(self._homeassistant_handler.status())
        return mqtt_status

    def mqtt_connection(self):
        return self._mqtt_handler.connection()

    def topic(self, relative_topic: str) -> str:
        return self._mqtt_handler.topic(relative_topic)

    def publish(
        self,
        relative_topic: str,
        payload: Any,
        qos=None,
        retain: bool = False,
        wait_for_publish: bool = False,
    ):
        if qos is None:
            return self._mqtt_handler.publish(
                relative_topic=relative_topic,
                payload=payload,
                retain=retain,
                wait_for_publish=wait_for_publish,
            )
        return self._mqtt_handler.publish(
            relative_topic=relative_topic,
            payload=payload,
            qos=qos,
            retain=retain,
            wait_for_publish=wait_for_publish,
        )

    def publish_json(
        self,
        relative_topic: str,
        payload: Dict[str, Any],
        qos=None,
        retain: bool = False,
        wait_for_publish: bool = False,
    ):
        if qos is None:
            return self._mqtt_handler.publish_json(
                relative_topic=relative_topic,
                payload=payload,
                retain=retain,
                wait_for_publish=wait_for_publish,
            )
        return self._mqtt_handler.publish_json(
            relative_topic=relative_topic,
            payload=payload,
            qos=qos,
            retain=retain,
            wait_for_publish=wait_for_publish,
        )

    def _build_mqtt_model(self, runtime: Dict[str, Any]) -> MQTTConnectionModel:
        host = str(runtime.get("mqtt_host") or "").strip()
        port = int(runtime.get("mqtt_port") or 1883)
        username = str(runtime.get("mqtt_username") or "").strip()
        password = str(runtime.get("mqtt_password") or "")
        instance = self._normalize_topic_part(str(runtime.get("mqtt_instance") or ""))
        return MQTTConnectionModel(
            role=self._role,
            host=host,
            port=port,
            username=username,
            password=password,
            instance=instance,
            readable_name=self.readable_name,
        )

    def _build_homeassistant_model(self, runtime: Dict[str, Any]) -> HomeAssistantConnectionModel:
        enabled = bool(runtime.get("homeassistant_enabled", False))
        if self._role != "hub":
            enabled = False
        return HomeAssistantConnectionModel(
            role=self._role,
            enabled=enabled,
            origin_name=self.readable_name,
            schedule_resolution=1.0,
            publish_timeout=5.0,
        )

    def _normalize_topic_part(self, value: str) -> str:
        return str(value or "").strip().strip("/")
