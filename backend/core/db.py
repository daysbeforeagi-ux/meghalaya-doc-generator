"""SQLite-backed session store with async access."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from models.session import Session, SessionStatus

DB_PATH = Path(os.getenv("STORAGE_DIR", "/app/storage")) / "sessions.db"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/storage"))
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data       TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def save_session(session: Session) -> None:
    expires_at = session.created_at + timedelta(hours=SESSION_EXPIRY_HOURS)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO sessions (session_id, data, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET data = excluded.data
            """,
            (
                session.session_id,
                session.model_dump_json(),
                session.created_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        await db.commit()


async def load_session(session_id: str) -> Session | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT data, expires_at FROM sessions WHERE session_id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    expires_at = datetime.fromisoformat(row[1])
    if datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
        await delete_session(session_id)
        return None
    return Session.model_validate_json(row[0])


async def delete_session(session_id: str) -> None:
    session_dir = STORAGE_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await db.commit()


async def purge_expired() -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT session_id FROM sessions WHERE expires_at < ?", (now,)
        ) as cursor:
            expired = [row[0] async for row in cursor]
    for sid in expired:
        await delete_session(sid)
    return len(expired)


def session_dir(session_id: str) -> Path:
    path = STORAGE_DIR / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path
