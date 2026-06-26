"""Question-flow intake endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.db import load_session, save_session
from models.session import (
    DocType,
    IntakePayload,
    PressOptions,
    SessionPublic,
    SessionStatus,
    SpeakerInfo,
)
from api.sessions import _to_public

router = APIRouter(prefix="/sessions", tags=["intake"])


@router.patch("/{session_id}/intake", response_model=SessionPublic)
async def submit_intake(session_id: str, payload: IntakePayload) -> SessionPublic:
    session = await load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    if session.status not in (SessionStatus.intake, SessionStatus.review):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot update intake when session is in '{session.status}' state.",
        )

    if payload.doc_type is not None:
        session.doc_type = payload.doc_type
        if payload.doc_type == DocType.speech:
            session.press_options = None
        else:
            session.speaker = None

    if payload.speaker_role is not None and session.doc_type == DocType.speech:
        session.speaker = SpeakerInfo(
            role=payload.speaker_role,
            name=payload.speaker_name if payload.speaker_role.value == "other" else None,
        )

    if payload.use_pictures is not None and session.doc_type == DocType.press_release:
        session.press_options = PressOptions(use_pictures=payload.use_pictures)

    if payload.brief is not None:
        session.brief = payload.brief.strip()

    if payload.length_target is not None:
        session.length_target = payload.length_target

    await save_session(session)
    return _to_public(session)
