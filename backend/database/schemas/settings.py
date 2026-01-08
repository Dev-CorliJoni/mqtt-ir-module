import sqlite3
import time
from typing import Optional, Dict, Any, Tuple

from database.database_base import DatabaseBase


LEARNING_DEFAULTS = {
    "press_takes_default": 5,
    "capture_timeout_ms_default": 3000,
    "hold_idle_timeout_ms": 300,
    "aggregate_round_to_us": 10,
    "aggregate_min_match_ratio": 0.6,
}

LEARNING_KEY_MAP = {
    "press_takes_default": "learning.press_takes_default",
    "capture_timeout_ms_default": "learning.capture_timeout_ms_default",
    "hold_idle_timeout_ms": "learning.hold_idle_timeout_ms",
    "aggregate_round_to_us": "learning.aggregate_round_to_us",
    "aggregate_min_match_ratio": "learning.aggregate_min_match_ratio",
}


class Settings(DatabaseBase):
    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )

    def get(self, key: str, default: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
        key = (key or "").strip()
        if not key:
            return default

        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            if not row:
                return default
            return str(row["value"])
        finally:
            if close:
                c.close()

    def set(self, key: str, value: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        key = (key or "").strip()
        if not key:
            raise ValueError("key must not be empty")

        c, close = self._use_conn(conn)
        try:
            now = time.time()
            c.execute(
                "INSERT OR REPLACE INTO app_settings(key, value, updated_at) VALUES(?, ?, ?)",
                (key, str(value), now),
            )
            c.commit()
            row = c.execute("SELECT key, value, updated_at FROM app_settings WHERE key = ?", (key,)).fetchone()
            if not row:
                raise ValueError("Failed to set setting")
            return dict(row)
        finally:
            if close:
                c.close()

    def get_learning_defaults(self) -> Dict[str, Any]:
        # Keep a copy so callers cannot mutate module constants.
        return dict(LEARNING_DEFAULTS)

    def get_learning_settings(self, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        # Read learning settings with safe fallbacks for UI + API defaults.
        return {
            "press_takes_default": self._read_int_setting(
                LEARNING_KEY_MAP["press_takes_default"],
                default=LEARNING_DEFAULTS["press_takes_default"],
                min_value=1,
                max_value=50,
                conn=conn,
            ),
            "capture_timeout_ms_default": self._read_int_setting(
                LEARNING_KEY_MAP["capture_timeout_ms_default"],
                default=LEARNING_DEFAULTS["capture_timeout_ms_default"],
                min_value=100,
                max_value=60000,
                conn=conn,
            ),
            "hold_idle_timeout_ms": self._read_int_setting(
                LEARNING_KEY_MAP["hold_idle_timeout_ms"],
                default=LEARNING_DEFAULTS["hold_idle_timeout_ms"],
                min_value=50,
                max_value=2000,
                conn=conn,
            ),
            "aggregate_round_to_us": self._read_int_setting(
                LEARNING_KEY_MAP["aggregate_round_to_us"],
                default=LEARNING_DEFAULTS["aggregate_round_to_us"],
                min_value=1,
                max_value=1000,
                conn=conn,
            ),
            "aggregate_min_match_ratio": self._read_float_setting(
                LEARNING_KEY_MAP["aggregate_min_match_ratio"],
                default=LEARNING_DEFAULTS["aggregate_min_match_ratio"],
                min_value=0.1,
                max_value=1.0,
                conn=conn,
            ),
        }

    def get_ui_settings(self, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        theme = self.get("ui.theme", default="system", conn=conn) or "system"
        language = self.get("ui.language", default="en", conn=conn) or "en"
        settings = {"theme": theme, "language": language}
        settings.update(self.get_learning_settings(conn=conn))
        return settings

    def update_ui_settings(
        self,
        theme: Optional[str] = None,
        language: Optional[str] = None,
        press_takes_default: Optional[int] = None,
        capture_timeout_ms_default: Optional[int] = None,
        hold_idle_timeout_ms: Optional[int] = None,
        aggregate_round_to_us: Optional[int] = None,
        aggregate_min_match_ratio: Optional[float] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        c, close = self._use_conn(conn)
        try:
            if theme is not None:
                self.set("ui.theme", str(theme), conn=c)
            if language is not None:
                self.set("ui.language", str(language), conn=c)
            if press_takes_default is not None:
                self.set(LEARNING_KEY_MAP["press_takes_default"], str(press_takes_default), conn=c)
            if capture_timeout_ms_default is not None:
                self.set(LEARNING_KEY_MAP["capture_timeout_ms_default"], str(capture_timeout_ms_default), conn=c)
            if hold_idle_timeout_ms is not None:
                self.set(LEARNING_KEY_MAP["hold_idle_timeout_ms"], str(hold_idle_timeout_ms), conn=c)
            if aggregate_round_to_us is not None:
                self.set(LEARNING_KEY_MAP["aggregate_round_to_us"], str(aggregate_round_to_us), conn=c)
            if aggregate_min_match_ratio is not None:
                self.set(LEARNING_KEY_MAP["aggregate_min_match_ratio"], str(aggregate_min_match_ratio), conn=c)
            return self.get_ui_settings(conn=c)
        finally:
            if close:
                c.close()

    def _read_int_setting(
        self,
        key: str,
        default: int,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> int:
        raw = self.get(key, default=None, conn=conn)
        if raw is None:
            return default
        try:
            value = int(str(raw).strip())
        except Exception:
            return default
        if min_value is not None and value < min_value:
            return default
        if max_value is not None and value > max_value:
            return default
        return value

    def _read_float_setting(
        self,
        key: str,
        default: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> float:
        raw = self.get(key, default=None, conn=conn)
        if raw is None:
            return default
        try:
            value = float(str(raw).strip())
        except Exception:
            return default
        if min_value is not None and value < min_value:
            return default
        if max_value is not None and value > max_value:
            return default
        return value
