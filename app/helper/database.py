# app/helper/database.py
import os
import sqlite3
import time
from typing import Optional, List, Dict, Any


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

    def init(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL
                );

                -- Single table for learned codes + optional mapping (action_name)
                CREATE TABLE IF NOT EXISTS ir_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    code_value TEXT NOT NULL,
                    action_name TEXT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE,
                    UNIQUE(device_id, code_value)
                );

                -- Enforce "action_name unique per device" only when action_name is set
                CREATE UNIQUE INDEX IF NOT EXISTS ux_ir_codes_device_action
                ON ir_codes(device_id, action_name)
                WHERE action_name IS NOT NULL;
                """
            )
            conn.commit()
        finally:
            conn.close()

    def create_device(self, name: str) -> Dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("Device name must not be empty")

        conn = self._connect()
        try:
            now = time.time()
            conn.execute("INSERT OR IGNORE INTO devices(name, created_at) VALUES(?, ?)", (name, now))
            conn.commit()
            row = conn.execute("SELECT id, name, created_at FROM devices WHERE name = ?", (name,)).fetchone()
            assert row is not None
            return dict(row)
        finally:
            conn.close()

    def list_devices(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT id, name, created_at FROM devices ORDER BY name").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _device_id(self, conn: sqlite3.Connection, device_name: str) -> int:
        row = conn.execute("SELECT id FROM devices WHERE name = ?", (device_name,)).fetchone()
        if not row:
            raise ValueError("Unknown device")
        return int(row["id"])

    def add_learned_code(self, device_name: str, code_value: str) -> Dict[str, Any]:
        conn = self._connect()
        try:
            self.create_device(device_name)
            device_id = self._device_id(conn, device_name)
            now = time.time()

            conn.execute(
                "INSERT OR IGNORE INTO ir_codes(device_id, code_value, action_name, created_at) VALUES(?, ?, NULL, ?)",
                (device_id, code_value, now),
            )
            conn.commit()

            row = conn.execute(
                """
                SELECT c.id, d.name AS device_name, c.code_value, c.action_name, c.created_at
                FROM ir_codes c
                JOIN devices d ON d.id = c.device_id
                WHERE c.device_id = ? AND c.code_value = ?
                """,
                (device_id, code_value),
            ).fetchone()
            assert row is not None
            return dict(row)
        finally:
            conn.close()

    def list_codes(self, device_name: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            if device_name:
                device_id = self._device_id(conn, device_name)
                rows = conn.execute(
                    """
                    SELECT c.id, d.name AS device_name, c.code_value, c.action_name, c.created_at
                    FROM ir_codes c
                    JOIN devices d ON d.id = c.device_id
                    WHERE c.device_id = ?
                    ORDER BY c.created_at DESC
                    """,
                    (device_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT c.id, d.name AS device_name, c.code_value, c.action_name, c.created_at
                    FROM ir_codes c
                    JOIN devices d ON d.id = c.device_id
                    ORDER BY c.created_at DESC
                    """
                ).fetchall()

            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_recent_codes(self, limit: int) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT c.id, d.name AS device_name, c.code_value, c.action_name, c.created_at
                FROM ir_codes c
                JOIN devices d ON d.id = c.device_id
                ORDER BY c.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create_mapping(self, device_name: str, action_name: str, code_id: int) -> Dict[str, Any]:
        device_name = device_name.strip()
        action_name = action_name.strip()
        if not device_name or not action_name:
            raise ValueError("device_name and action_name must not be empty")

        conn = self._connect()
        try:
            self.create_device(device_name)
            device_id = self._device_id(conn, device_name)

            code_row = conn.execute(
                "SELECT id, device_id FROM ir_codes WHERE id = ?",
                (code_id,),
            ).fetchone()
            if not code_row:
                raise ValueError("Unknown code_id")
            if int(code_row["device_id"]) != device_id:
                raise ValueError("code_id does not belong to device")

            # This can raise sqlite3.IntegrityError if action_name already used on same device
            conn.execute(
                "UPDATE ir_codes SET action_name = ? WHERE id = ?",
                (action_name, code_id),
            )
            conn.commit()

            row = conn.execute(
                """
                SELECT c.id, d.name AS device_name, c.action_name, c.code_value, c.created_at
                FROM ir_codes c
                JOIN devices d ON d.id = c.device_id
                WHERE c.id = ?
                """,
                (code_id,),
            ).fetchone()
            assert row is not None
            return dict(row)
        finally:
            conn.close()

    def list_mappings(self, device_name: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            if device_name:
                device_id = self._device_id(conn, device_name)
                rows = conn.execute(
                    """
                    SELECT c.id, d.name AS device_name, c.action_name, c.code_value, c.created_at
                    FROM ir_codes c
                    JOIN devices d ON d.id = c.device_id
                    WHERE c.device_id = ? AND c.action_name IS NOT NULL
                    ORDER BY c.action_name
                    """,
                    (device_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT c.id, d.name AS device_name, c.action_name, c.code_value, c.created_at
                    FROM ir_codes c
                    JOIN devices d ON d.id = c.device_id
                    WHERE c.action_name IS NOT NULL
                    ORDER BY d.name, c.action_name
                    """
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
            