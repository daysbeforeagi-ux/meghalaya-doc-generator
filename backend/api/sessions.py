"""Session creation and retrieval endpoints."""

from __future__ import annotations

import os
import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from core.db import load_session, save_session
from models.session import Session, SessionPublic

router = APIRouter(prefix="/sessions", tags=["sessions"])

_ALPHABET = string.ascii_letters + string.digits
_MAX_SESSIONS_PER_IP = int(os.getenv("RATE_LIMIT_PER_IP", "10"))
_ip_counts: dict[str, int] = {}


def _mint_id() -> str:
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(22))
    return f"usr_{suffix}"


@router.post("", response_model=SessionPublic, status_code=201)
async def create_session(request: Request) -> SessionPublic:
    client_ip = request.client.host if request.client else "unknown"
    count = _ip_counts.get(client_ip, 0)
    if count >= _MAX_SESSIONS_PER_IP:
        raise HTTPException(status_code=429, detail="Too many sessions from this IP.")
    _ip_counts[client_ip] = count + 1

    session = Session(
        session_id=_mint_id(),
        created_at=datetime.now(timezone.utc),
    )
    await save_session(session)
    return _to_public(session)


@router.get("/{session_id}", response_model=SessionPublic)
async def get_session(session_id: str) -> SessionPublic:
    session = await load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return _to_public(session)


def _to_public(session: Session) -> SessionPublic:
    return SessionPublic(
        session_id=session.session_id,
        status=session.status,
        doc_type=session.doc_type,
        brief=session.brief,
        length_target=session.length_target,
        error_message=session.error_message,
        deliverable_ready=session.deliverable_path is not None,
        dossier_ready=session.dossier_path is not None,
    )
