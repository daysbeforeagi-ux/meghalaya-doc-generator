"""Generation trigger and status/download endpoints."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from core.db import load_session, save_session, session_dir
from core.style import get_or_extract
from core.research import run_research
from core.generator import generate_draft
from core.render import build_deliverable, build_dossier
from models.session import Session, SessionPublic, SessionStatus
from api.sessions import _to_public

router = APIRouter(prefix="/sessions", tags=["generate"])


def _read_uploads(session: Session) -> list[str]:
    from pypdf import PdfReader

    texts: list[str] = []
    base = session_dir(session.session_id) / "docs"
    if not base.exists():
        return texts
    for ref in session.uploads:
        fname = ref.replace("upload://docs/", "")
        path = base / fname
        if not path.exists():
            continue
        if path.suffix.lower() == ".pdf":
            try:
                reader = PdfReader(str(path))
                texts.append("\n".join(p.extract_text() or "" for p in reader.pages))
            except Exception:
                pass
        else:
            texts.append(path.read_text(errors="replace"))
    return texts


async def _run_pipeline(session_id: str) -> None:
    session = await load_session(session_id)
    if session is None:
        return

    try:
        # Research
        session.status = SessionStatus.researching
        await save_session(session)
        evidence = await run_research(session)
        session.evidence = evidence

        # Style profile
        category = "speech" if session.doc_type and session.doc_type.value == "speech" else "press_release"
        style_profile = await asyncio.to_thread(get_or_extract, category)
        session.style_profile_ref = f"{category}_profile.json"

        # Upload text extraction
        upload_texts = await asyncio.to_thread(_read_uploads, session)

        # Generation
        session.status = SessionStatus.drafting
        await save_session(session)
        draft, claim_map = await asyncio.to_thread(
            generate_draft, session, style_profile, upload_texts
        )

        # Render DOCX
        out_dir = session_dir(session_id)
        deliverable_path = out_dir / "deliverable.docx"
        dossier_path = out_dir / "dossier.docx"
        await asyncio.to_thread(build_deliverable, session, draft, deliverable_path)
        await asyncio.to_thread(build_dossier, session, draft, claim_map, evidence, dossier_path)

        session.deliverable_path = str(deliverable_path)
        session.dossier_path = str(dossier_path)
        session.status = SessionStatus.review

    except Exception as exc:
        session.status = SessionStatus.error
        session.error_message = str(exc)

    await save_session(session)


@router.post("/{session_id}/generate", response_model=SessionPublic)
async def trigger_generate(session_id: str, background_tasks: BackgroundTasks) -> SessionPublic:
    session = await load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    if not session.doc_type:
        raise HTTPException(status_code=422, detail="doc_type is required before generating.")
    if not session.brief:
        raise HTTPException(status_code=422, detail="brief is required before generating.")
    if session.status in (SessionStatus.researching, SessionStatus.drafting):
        raise HTTPException(status_code=409, detail="Generation already in progress.")

    session.status = SessionStatus.researching
    session.error_message = None
    session.deliverable_path = None
    session.dossier_path = None
    await save_session(session)

    background_tasks.add_task(_run_pipeline, session_id)
    return _to_public(session)


@router.get("/{session_id}/download/deliverable")
async def download_deliverable(session_id: str) -> FileResponse:
    session = await load_session(session_id)
    if session is None or not session.deliverable_path:
        raise HTTPException(status_code=404, detail="Deliverable not ready.")
    path = Path(session.deliverable_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    fname = "draft_deliverable.docx"
    return FileResponse(str(path), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=fname)


@router.get("/{session_id}/download/dossier")
async def download_dossier(session_id: str) -> FileResponse:
    session = await load_session(session_id)
    if session is None or not session.dossier_path:
        raise HTTPException(status_code=404, detail="Dossier not ready.")
    path = Path(session.dossier_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(str(path), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename="sources_dossier.docx")
