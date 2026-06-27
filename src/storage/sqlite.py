"""
SQLite-backed StorageRepo (§4, §14).
All keys are scoped by session_id; created_at and last_activity stamped on every row.
Swap this module for an object-store implementation in M3 without touching callers.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.intake.models import Session


class SQLiteRepo:
    """Thread-safe SQLite implementation of StorageRepo."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._local = threading.local()
        self._migrate()

    def _conn(self) -> sqlite3.Connection:
        """One connection per thread."""
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return self._local.conn

    def _migrate(self) -> None:
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                created_at   TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                status       TEXT NOT NULL,
                data         TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_status
                ON sessions (status);
            CREATE INDEX IF NOT EXISTS idx_sessions_last_activity
                ON sessions (last_activity);
        """)
        conn.commit()

    def create_session(self, session: Session) -> None:
        conn = self._conn()
        conn.execute(
            """
            INSERT INTO sessions (session_id, created_at, last_activity, status, data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.created_at.isoformat(),
                session.last_activity.isoformat(),
                session.status,
                session.model_dump_json(),
            ),
        )
        conn.commit()

    def get_session(self, session_id: str) -> Optional[Session]:
        row = self._conn().execute(
            "SELECT data FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return Session.model_validate_json(row["data"])

    def update_session(self, session: Session) -> None:
        session.last_activity = datetime.now(timezone.utc)
        conn = self._conn()
        conn.execute(
            """
            UPDATE sessions
            SET last_activity = ?, status = ?, data = ?
            WHERE session_id = ?
            """,
            (
                session.last_activity.isoformat(),
                session.status,
                session.model_dump_json(),
                session.session_id,
            ),
        )
        conn.commit()

    def close(self) -> None:
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            del self._local.conn
