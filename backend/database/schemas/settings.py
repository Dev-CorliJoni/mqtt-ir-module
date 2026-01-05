import sqlite3
import time
from typing import Optional, Dict, Any, Tuple

from database.database_base import DatabaseBase


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

    def get_ui_settings(self, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        theme = self.get("ui.theme", default="system", conn=conn) or "system"
        language = self.get("ui.language", default="en", conn=conn) or "en"
        return {"theme": theme, "language": language}

    def update_ui_settings(
        self,
        theme: Optional[str] = None,
        language: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        c, close = self._use_conn(conn)
        try:
            if theme is not None:
                self.set("ui.theme", str(theme), conn=c)
            if language is not None:
                self.set("ui.language", str(language), conn=c)
            return self.get_ui_settings(conn=c)
        finally:
            if close:
                c.close()
                