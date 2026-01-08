import os
from typing import Optional


class Environment:
    def __init__(self) -> None:
        self.api_key = os.getenv("API_KEY", "").strip()
        self.ir_device = os.getenv("IR_DEVICE", "/dev/lirc0").strip()
        self.data_folder = os.getenv("DATA_DIR", "/data").strip()

        # Public base url for reverse-proxy sub-path hosting (e.g. /mqtt-ir-module/)
        self.public_base_url = self._normalize_base_url(os.getenv("PUBLIC_BASE_URL", "/"))

        # Optional: if set, the backend will inject it into the frontend runtime config.
        # WARNING: This exposes the key to any browser that can access the UI.
        self.public_api_key = os.getenv("PUBLIC_API_KEY", "").strip()

        self.debug = self._read_bool("DEBUG", default=False)

        # ir-ctl receiver options
        self.ir_wideband = self._read_bool("IR_WIDEBAND", default=False)

        # Learning defaults live in app settings (see database.settings).

    def _read_bool(self, name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        value = raw.strip().lower()
        if value in ("1", "true", "yes", "y", "on"):
            return True
        if value in ("0", "false", "no", "n", "off"):
            return False
        return default

    def _read_int(self, name: str, default: int, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(raw.strip())
        except Exception:
            return default
        if min_value is not None and value < min_value:
            return default
        if max_value is not None and value > max_value:
            return default
        return value

    def _read_float(
        self,
        name: str,
        default: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> float:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = float(raw.strip())
        except Exception:
            return default
        if min_value is not None and value < min_value:
            return default
        if max_value is not None and value > max_value:
            return default
        return value

    def _normalize_base_url(self, raw: Optional[str]) -> str:
        value = (raw or "/").strip()
        if not value:
            return "/"
        if not value.startswith("/"):
            value = "/" + value
        if not value.endswith("/"):
            value += "/"
        # Collapse accidental double slash root
        if value == "//":
            return "/"
        return value
