"""
Abstract storage interface. M1 implementation: SQLite (sqlite.py).
M3 swap: replace SQLiteRepo with an object-store + purge implementation
that satisfies this same Protocol — no other module needs to change.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from src.intake.models import Session


@runtime_checkable
class StorageRepo(Protocol):
    def create_session(self, session: Session) -> None: ...
    def get_session(self, session_id: str) -> Optional[Session]: ...
    def update_session(self, session: Session) -> None: ...
    def close(self) -> None: ...
