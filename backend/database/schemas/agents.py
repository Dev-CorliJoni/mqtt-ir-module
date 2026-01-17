import json
import sqlite3
import time
from typing import Optional, Dict, Any, List

from database.database_base import DatabaseBase


class Agents(DatabaseBase):
    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NULL,
                transport TEXT NOT NULL,
                status TEXT NOT NULL,
                capabilities_json TEXT NULL,
                last_seen REAL NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )

    def upsert(
        self,
        agent_id: str,
        name: Optional[str],
        transport: str,
        status: str,
        capabilities: Optional[Dict[str, Any]],
        last_seen: Optional[float],
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        agent_id = (agent_id or "").strip()
        if not agent_id:
            raise ValueError("agent_id must not be empty")

        c, close = self._use_conn(conn)
        try:
            now = time.time()
            cap_json = json.dumps(capabilities) if capabilities is not None else None
            existing = c.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
            if existing:
                c.execute(
                    """
                    UPDATE agents
                    SET name = ?,
                        transport = ?,
                        status = ?,
                        capabilities_json = ?,
                        last_seen = ?,
                        updated_at = ?
                    WHERE agent_id = ?
                    """,
                    (name, transport, status, cap_json, last_seen, now, agent_id),
                )
            else:
                c.execute(
                    """
                    INSERT INTO agents(
                        agent_id,
                        name,
                        transport,
                        status,
                        capabilities_json,
                        last_seen,
                        created_at,
                        updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (agent_id, name, transport, status, cap_json, last_seen, now, now),
                )
            c.commit()
            row = c.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
            if not row:
                raise ValueError("Failed to upsert agent")
            return self._row_to_dict(row)
        finally:
            if close:
                c.close()

    def set_status(self, agent_id: str, status: str, last_seen: Optional[float] = None, conn: Optional[sqlite3.Connection] = None) -> None:
        agent_id = (agent_id or "").strip()
        if not agent_id:
            return
        c, close = self._use_conn(conn)
        try:
            now = time.time()
            c.execute(
                "UPDATE agents SET status = ?, last_seen = ?, updated_at = ? WHERE agent_id = ?",
                (status, last_seen, now, agent_id),
            )
            c.commit()
        finally:
            if close:
                c.close()

    def touch(self, agent_id: str, last_seen: Optional[float], conn: Optional[sqlite3.Connection] = None) -> None:
        agent_id = (agent_id or "").strip()
        if not agent_id:
            return
        c, close = self._use_conn(conn)
        try:
            now = time.time()
            c.execute(
                "UPDATE agents SET last_seen = ?, updated_at = ? WHERE agent_id = ?",
                (last_seen, now, agent_id),
            )
            c.commit()
        finally:
            if close:
                c.close()

    def get(self, agent_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
        agent_id = (agent_id or "").strip()
        if not agent_id:
            return None
        c, close = self._use_conn(conn)
        try:
            row = c.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
            return self._row_to_dict(row) if row else None
        finally:
            if close:
                c.close()

    def list(self, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
        c, close = self._use_conn(conn)
        try:
            rows = c.execute(
                "SELECT * FROM agents ORDER BY name, agent_id"
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            if close:
                c.close()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        raw = data.get("capabilities_json")
        if raw:
            try:
                data["capabilities"] = json.loads(str(raw))
            except Exception:
                data["capabilities"] = None
        else:
            data["capabilities"] = None
        data.pop("capabilities_json", None)
        return data
