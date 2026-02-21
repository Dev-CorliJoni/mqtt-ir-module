from typing import Any, Dict

from database.schemas.settings import Settings


class AgentBindingStore:
    def __init__(self, settings_store: Settings) -> None:
        self._settings_store = settings_store

    def is_bound(self) -> bool:
        return bool(self.hub_id())

    def hub_id(self) -> str:
        return str(self._settings_store.get("pairing_hub_id", default="") or "").strip()

    def hub_topic(self) -> str:
        return str(self._settings_store.get("pairing_hub_topic", default="") or "").strip()

    def clear_binding(self) -> None:
        self._settings_store.set("pairing_hub_id", "")
        self._settings_store.set("pairing_hub_topic", "")
        self._settings_store.set("pairing_hub_name", "")
        self._settings_store.set("pairing_session_id", "")
        self._settings_store.set("pairing_nonce", "")
        self._settings_store.set("pairing_accepted_at", "")

    def set_binding(
        self,
        hub_id: str,
        hub_topic: str,
        hub_name: str,
        session_id: str,
        nonce: str,
        accepted_at: Any,
    ) -> None:
        self._settings_store.set("pairing_hub_id", str(hub_id or ""))
        self._settings_store.set("pairing_hub_topic", str(hub_topic or ""))
        self._settings_store.set("pairing_hub_name", str(hub_name or ""))
        self._settings_store.set("pairing_session_id", str(session_id or ""))
        self._settings_store.set("pairing_nonce", str(nonce or ""))
        self._settings_store.set("pairing_accepted_at", str(accepted_at or ""))

    def binding_data(self) -> Dict[str, Any]:
        return {
            "pairing_hub_id": self._settings_store.get("pairing_hub_id", default=""),
            "pairing_hub_topic": self._settings_store.get("pairing_hub_topic", default=""),
            "pairing_hub_name": self._settings_store.get("pairing_hub_name", default=""),
            "pairing_session_id": self._settings_store.get("pairing_session_id", default=""),
            "pairing_nonce": self._settings_store.get("pairing_nonce", default=""),
            "pairing_accepted_at": self._settings_store.get("pairing_accepted_at", default=""),
        }
