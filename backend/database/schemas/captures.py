import sqlite3
import time
from typing import Optional, Dict, Any

from database.database_base import DatabaseBase


class Captures(DatabaseBase):
    # -----------------------------
    # Schema / migrations
    # -----------------------------

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                button_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                take_index INTEGER NOT NULL,
                raw_text TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY(button_id) REFERENCES buttons(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS ix_captures_button_id ON captures(button_id);
            """
        )
        
    # -----------------------------
    # Captures (debug)
    # -----------------------------

    def create(
        self,
        button_id: int,
        mode: str,
        take_index: int,
        raw_text: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        mode = mode.strip().lower()
        if mode not in ("press", "hold"):
            raise ValueError("mode must be 'press' or 'hold'")
        if take_index < 0:
            raise ValueError("take_index must be >= 0")

        c, close = self._use_conn(conn)
        try:
            now = time.time()
            c.execute(
                "INSERT INTO captures(button_id, mode, take_index, raw_text, created_at) VALUES(?, ?, ?, ?, ?)",
                (button_id, mode, take_index, raw_text, now),
            )
            c.commit()
            row = c.execute(
                "SELECT id, button_id, mode, take_index, raw_text, created_at FROM captures WHERE id = last_insert_rowid()"
            ).fetchone()
            if not row:
                raise ValueError("Failed to create capture")
            return dict(row)
        finally:
            if close:
                c.close()

    def clear(self, conn: Optional[sqlite3.Connection] = None) -> None:
        c, close = self._use_conn(conn)
        try:
            c.execute("DELETE FROM captures")
            c.commit()
        finally:
            if close:
                c.close()
