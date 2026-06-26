"""File upload endpoint — documents and images."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.db import load_session, save_session, session_dir
from models.session import SessionStatus

router = APIRouter(prefix="/sessions", tags=["upload"])

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
ALLOWED_DOC_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/{session_id}/upload")
async def upload_file(session_id: str, file: UploadFile = File(...)) -> dict:
    session = await load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    if session.status not in (SessionStatus.intake, SessionStatus.review):
        raise HTTPException(status_code=409, detail="Uploads only allowed during intake.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {os.getenv('MAX_UPLOAD_MB', '20')} MB limit.",
        )

    guessed_type = mimetypes.guess_type(file.filename or "")[0] or ""
    if guessed_type not in ALLOWED_DOC_TYPES | ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Allowed: PDF, DOCX, TXT, JPEG, PNG, WEBP.",
        )

    is_image = guessed_type in ALLOWED_IMAGE_TYPES
    if is_image and (not session.press_options or not session.press_options.use_pictures):
        raise HTTPException(
            status_code=400,
            detail="Image uploads are only allowed when 'use_pictures' is enabled.",
        )

    upload_folder = session_dir(session_id) / ("images" if is_image else "docs")
    upload_folder.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload").name
    dest = upload_folder / safe_name
    dest.write_bytes(content)

    ref = f"upload://{('images' if is_image else 'docs')}/{safe_name}"
    if is_image:
        if session.press_options:
            session.press_options.image_refs.append(ref)
    else:
        session.uploads.append(ref)

    await save_session(session)
    return {"ref": ref, "size": len(content), "type": guessed_type}
