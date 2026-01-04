import os
from typing import Optional


class Environment:
    def __init__(self) -> None:
        self.api_key = os.getenv("API_KEY", "").strip()
        self.ir_device = os.getenv("IR_DEVICE", "/dev/lirc0").strip()
        self.data_folder = os.getenv("DATA_DIR", "/data").strip()

        self.debug = self._read_bool("DEBUG", default=False)

        # ir-ctl receiver options
        self.ir_wideband = self._read_bool("IR_WIDEBAND", default=False)

        # Learning defaults (the API can override these per request)
        self.press_takes_default = self._read_int("PRESS_TAKES_DEFAULT", default=5, min_value=1, max_value=50)
        self.capture_timeout_ms_default = self._read_int("CAPTURE_TIMEOUT_MS_DEFAULT", default=3000, min_value=100, max_value=60000)
        self.hold_idle_timeout_ms = self._read_int("HOLD_IDLE_TIMEOUT_MS", default=300, min_value=50, max_value=2000)

        # Aggregation defaults
        self.aggregate_round_to_us = self._read_int("AGGREGATE_ROUND_TO_US", default=10, min_value=1, max_value=1000)
        self.aggregate_min_match_ratio = self._read_float("AGGREGATE_MIN_MATCH_RATIO", default=0.6, min_value=0.1, max_value=1.0)

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

    def _read_float(self, name: str, default: float, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
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
