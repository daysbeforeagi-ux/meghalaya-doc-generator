"""
Orator — FastAPI entrypoint (M1).
Pipeline: intake → style → research → generate → sentinel → gate → deliver → audit.
Gate checks run before delivery; audit is written either way.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.audit.gate import run_gate_checks
from src.audit.log import AuditLogger
from src.config import (
    DB_PATH,
    OUTPUTS_DIR,
    PROFILES_DIR,
    RATE_LIMIT_GENERATE,
    RATE_LIMIT_SESSION,
)
from src.generate.generator import generate_speech
from src.intake.flow import build_session_from_request
from src.intake.models import CreateSessionRequest
from src.render.dossier import write_dossier_docx
from src.render.docx_writer import write_speech_docx
from src.render.sentinel import process_sentinels
from src.research.pipeline import run_research
from src.storage.sqlite import SQLiteRepo
from src.style.extractor import load_or_extract_profile

# Per-IP rate limiter (§4) — reads X-Real-IP set by Nginx, falls back to peer addr
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)

_repo: Optional[SQLiteRepo] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _repo
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    _repo = SQLiteRepo(DB_PATH)
    yield
    _repo.close()


app = FastAPI(title="Orator API — M1", version="1.0.0", lifespan=lifespan)

# Rate limiter state + 429 handler (§4)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow same-origin Nginx proxy in prod; also allow localhost in dev
_site_domain = os.getenv("SITE_DOMAIN", "")
_cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if _site_domain:
    _cors_origins += [f"https://{_site_domain}", f"http://{_site_domain}"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db() -> SQLiteRepo:
    if _repo is None:
        raise HTTPException(500, "Storage not initialised")
    return _repo


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/generate", status_code=202)
@limiter.limit(RATE_LIMIT_GENERATE)
async def create_and_generate(request: Request, response: Response, body: CreateSessionRequest, background_tasks: BackgroundTasks):
    """
    Accept Q1–Q5 intake answers, create a session, and kick off the pipeline.
    Returns immediately with session_id; client polls /api/sessions/{id} for status.
    """
    db = _db()
    session = build_session_from_request(body)
    db.create_session(session)
    background_tasks.add_task(_run_pipeline, session.session_id)
    return {"session_id": session.session_id, "status": "processing"}


@app.get("/api/sessions/{session_id}")
@limiter.limit(RATE_LIMIT_SESSION)
async def get_session(request: Request, response: Response, session_id: str):
    session = _db().get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session.session_id,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "error_message": session.error_message,
        "has_deliverable": session.deliverable_path is not None,
        "has_dossier": session.dossier_path is not None,
    }


@app.get("/api/sessions/{session_id}/download/deliverable")
async def download_deliverable(session_id: str):
    session = _db().get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    if not session.deliverable_path:
        raise HTTPException(404, "Deliverable not ready yet")
    path = Path(session.deliverable_path)
    if not path.exists():
        raise HTTPException(404, "Deliverable file missing from storage")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"speech_{session_id[:12]}.docx",
    )


@app.get("/api/sessions/{session_id}/download/dossier")
async def download_dossier(session_id: str):
    session = _db().get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    if not session.dossier_path:
        raise HTTPException(404, "Dossier not ready yet")
    path = Path(session.dossier_path)
    if not path.exists():
        raise HTTPException(404, "Dossier file missing from storage")
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"sources_dossier_{session_id[:12]}.docx",
    )


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def _run_pipeline(session_id: str) -> None:
    """
    Full M1 pipeline. Every stage writes to the audit log.
    Gate checks run before delivery; audit is written on failure too.
    """
    db = _db()
    session = db.get_session(session_id)
    if session is None:
        return

    loop = asyncio.get_event_loop()

    with AuditLogger(session_id) as logger:
        try:
            # 1. Load / extract style profile (§7)
            profile = await loop.run_in_executor(None, load_or_extract_profile, "speech")
            logger.log(
                "style_profile",
                quality=profile.quality,
                source_hash=profile.source_hash,
                corpus_size=profile.corpus_size,
            )
            if profile.quality == "insufficient":
                logger.log_error("Style profile quality is 'insufficient' — output style may be poor", "style")

            # 2. Research (§8) — synchronous in M1, parallelism deferred to M4
            session.status = "researching"
            db.update_session(session)

            research = await loop.run_in_executor(None, run_research, session, logger)

            if research.budget_exhausted:
                logger.log("research_budget_exhausted", omitted=research.omitted_facts)

            session.evidence = research.evidence
            session.status = "drafting"
            db.update_session(session)

            # 3. Generate with sentinel tags (§11)
            raw_text = await loop.run_in_executor(
                None, generate_speech, session, profile, research.evidence, logger
            )

            # 4. Sentinel processing → clean text + Dossier entries (§12.3)
            gen_result = process_sentinels(
                raw_text,
                research.evidence,
                research.omitted_facts,
                research.sensitive_flags,
            )

            # 5. Gate checks — BEFORE delivery; audit either way (§13)
            gate = run_gate_checks(gen_result, research.evidence, session.length_target)
            logger.log_gate_check(gate.passed, gate.warnings)

            # 6. Write .docx outputs (§12.1, §12.2)
            out_dir = OUTPUTS_DIR / session_id
            out_dir.mkdir(parents=True, exist_ok=True)

            deliverable_path = out_dir / "deliverable.docx"
            dossier_path = out_dir / "dossier.docx"

            speaker_name: Optional[str] = None
            if session.speaker:
                speaker_name = session.speaker.name or session.speaker.role.replace("_", " ").title()

            write_speech_docx(gen_result.clean_text, deliverable_path, speaker_name)
            write_dossier_docx(
                gen_result.dossier_entries,
                gate,
                gen_result.omitted_facts,
                gen_result.sensitive_flags,
                dossier_path,
            )

            logger.log_delivery(str(deliverable_path), str(dossier_path))

            # 7. Persist outputs; status = "done" if gate passed, else "review" for human
            session.deliverable_path = str(deliverable_path)
            session.dossier_path = str(dossier_path)
            session.audit_ref = f"audit://{session_id}/audit.jsonl"
            session.status = "done" if gate.passed else "review"
            db.update_session(session)

        except Exception as exc:
            logger.log_error(str(exc), "pipeline")
            session.status = "error"
            session.error_message = str(exc)[:500]
            db.update_session(session)
            raise
