import os
import sqlite3
from typing import Optional, Tuple


class DatabaseBase:
    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        self._db_path = os.path.join(self._data_dir, "ir.db")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _use_conn(self, conn: Optional[sqlite3.Connection]) -> Tuple[sqlite3.Connection, bool]:
        if conn is not None:
            return conn, False
        return self._connect(), True
