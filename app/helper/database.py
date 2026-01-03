import hashlib
import os
import re
import sqlite3
import time
from typing import Optional, List, Dict, Any, Tuple


class Database:
    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        self._db_path = os.path.join(self._data_dir, "ir.db")

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(self._data_dir, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _use_conn(self, conn: Optional[sqlite3.Connection]) -> Tuple[sqlite3.Connection, bool]:
        if conn is not None:
            return conn, False
        return self._connect(), True

    def init(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    lirc_name TEXT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ir_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    code_value TEXT NOT NULL,
                    action_name TEXT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE,
                    UNIQUE(device_id, code_value)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS ux_ir_codes_device_action
                ON ir_codes(device_id, action_name)
                WHERE action_name IS NOT NULL;
                """
            )

            # Backfill lirc_name for existing devices if missing
            rows = conn.execute("SELECT id, name, lirc_name FROM devices").fetchall()
            for r in rows:
                if not (r["lirc_name"] and str(r["lirc_name"]).strip()):
                    lirc_name = self._make_lirc_name(str(r["name"]))
                    conn.execute("UPDATE devices SET lirc_name = ? WHERE id = ?", (lirc_name, int(r["id"])))

            conn.commit()
        finally:
            conn.close()

    def _make_lirc_name(self, device_name: str) -> str:
        raw = device_name.strip()
        base = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
        if not base:
            base = "device"
        suffix = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6]
        return f"{base}_{suffix}"

    def get_lirc_name(self, device_id: int, conn: Optional[sqlite3.Connection] = None) -> str:
        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT lirc_name FROM devices WHERE id = ?", (device_id,)).fetchone()
            if not row:
                raise ValueError("Unknown device_id")
            lirc_name = str(row["lirc_name"] or "").strip()
            if not lirc_name:
                # Should not happen due to init/backfill, but keep safe.
                name_row = c.execute("SELECT name FROM devices WHERE id = ?", (device_id,)).fetchone()
                assert name_row is not None
                lirc_name = self._make_lirc_name(str(name_row["name"]))
                c.execute("UPDATE devices SET lirc_name = ? WHERE id = ?", (lirc_name, device_id))
                c.commit()
            return lirc_name
        finally:
            if close:
                c.close()

    def create_device(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("Device name must not be empty")

        c, close = self._use_conn(conn)
        try:
            now = time.time()
            lirc_name = self._make_lirc_name(name)

            c.execute(
                "INSERT OR IGNORE INTO devices(name, lirc_name, created_at) VALUES(?, ?, ?)",
                (name, lirc_name, now),
            )
            # Ensure lirc_name exists (older rows)
            c.execute(
                """
                UPDATE devices
                SET lirc_name = ?
                WHERE name = ? AND (lirc_name IS NULL OR lirc_name = '')
                """,
                (lirc_name, name),
            )
            c.commit()

            row = c.execute("SELECT id, name, lirc_name, created_at FROM devices WHERE name = ?", (name,)).fetchone()
            assert row is not None
            return dict(row)
        finally:
            if close:
                c.close()

    def rename_device(self, device_id: int, name: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("Device name must not be empty")

        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
            if not row:
                raise ValueError("Unknown device_id")

            c.execute("UPDATE devices SET name = ? WHERE id = ?", (name, device_id))
            c.commit()

            out = c.execute("SELECT id, name, lirc_name, created_at FROM devices WHERE id = ?", (device_id,)).fetchone()
            assert out is not None
            return dict(out)
        finally:
            if close:
                c.close()

    def delete_device(self, device_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT id, name, lirc_name, created_at FROM devices WHERE id = ?", (device_id,)).fetchone()
            if not row:
                raise ValueError("Unknown device_id")

            c.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            c.commit()
            return dict(row)
        finally:
            if close:
                c.close()

    def get_device_by_name(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT id, name, lirc_name, created_at FROM devices WHERE name = ?", (name.strip(),)).fetchone()
            if not row:
                raise ValueError("Unknown device")
            return dict(row)
        finally:
            if close:
                c.close()

    def get_device(self, device_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT id, name, lirc_name, created_at FROM devices WHERE id = ?", (device_id,)).fetchone()
            if not row:
                raise ValueError("Unknown device_id")
            return dict(row)
        finally:
            if close:
                c.close()

    def list_devices(self, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
        c, close = self._use_conn(conn)
        try:
            rows = c.execute("SELECT id, name, lirc_name, created_at FROM devices ORDER BY name").fetchall()
            return [dict(r) for r in rows]
        finally:
            if close:
                c.close()

    def clear_codes_for_device(self, device_id: int, conn: Optional[sqlite3.Connection] = None) -> None:
        c, close = self._use_conn(conn)
        try:
            c.execute("DELETE FROM ir_codes WHERE device_id = ?", (device_id,))
            c.commit()
        finally:
            if close:
                c.close()

    def create_code(self, device_id: int, code_value: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        code_value = code_value.strip()
        if not code_value:
            raise ValueError("code_value must not be empty")

        c, close = self._use_conn(conn)
        try:
            now = time.time()
            # Ensure device exists
            row = c.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
            if not row:
                raise ValueError("Unknown device_id")

            c.execute(
                "INSERT OR IGNORE INTO ir_codes(device_id, code_value, action_name, created_at) VALUES(?, ?, NULL, ?)",
                (device_id, code_value, now),
            )
            c.commit()

            out = c.execute(
                """
                SELECT c.id, c.device_id, c.code_value, c.action_name, c.created_at
                FROM ir_codes c
                WHERE c.device_id = ? AND c.code_value = ?
                """,
                (device_id, code_value),
            ).fetchone()
            assert out is not None
            return dict(out)
        finally:
            if close:
                c.close()

    def update_code(self, code_id: int, action_name: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        action_name = action_name.strip()
        if not action_name:
            raise ValueError("action_name must not be empty")

        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT id FROM ir_codes WHERE id = ?", (code_id,)).fetchone()
            if not row:
                raise ValueError("Unknown code_id")

            # Can raise sqlite3.IntegrityError due to unique index per device on action_name
            c.execute("UPDATE ir_codes SET action_name = ? WHERE id = ?", (action_name, code_id))
            c.commit()

            out = c.execute(
                """
                SELECT c.id, c.device_id, c.code_value, c.action_name, c.created_at
                FROM ir_codes c
                WHERE c.id = ?
                """,
                (code_id,),
            ).fetchone()
            assert out is not None
            return dict(out)
        finally:
            if close:
                c.close()

    def delete_code(self, code_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        c, close = self._use_conn(conn)
        try:
            row = c.execute(
                "SELECT id, device_id, code_value, action_name, created_at FROM ir_codes WHERE id = ?",
                (code_id,),
            ).fetchone()
            if not row:
                raise ValueError("Unknown code_id")

            c.execute("DELETE FROM ir_codes WHERE id = ?", (code_id,))
            c.commit()
            return dict(row)
        finally:
            if close:
                c.close()

    def list_codes(self, device_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
        c, close = self._use_conn(conn)
        try:
            if device_id is None:
                rows = c.execute(
                    """
                    SELECT c.id, c.device_id, c.code_value, c.action_name, c.created_at,
                           d.name AS device_name, d.lirc_name AS lirc_name
                    FROM ir_codes c
                    JOIN devices d ON d.id = c.device_id
                    ORDER BY c.created_at DESC
                    """
                ).fetchall()
            else:
                rows = c.execute(
                    """
                    SELECT c.id, c.device_id, c.code_value, c.action_name, c.created_at,
                           d.name AS device_name, d.lirc_name AS lirc_name
                    FROM ir_codes c
                    JOIN devices d ON d.id = c.device_id
                    WHERE c.device_id = ?
                    ORDER BY c.created_at DESC
                    """,
                    (device_id,),
                ).fetchall()

            return [dict(r) for r in rows]
        finally:
            if close:
                c.close()
                
                