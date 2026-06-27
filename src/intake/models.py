"""
Canonical shared definitions (§5, §8.2, §12.3).
All modules import Session, EvidenceRecord, and the sentinel format from here.
Changing these shapes is a breaking change — update every importer.
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# ── Sentinel format (§12.3) ──────────────────────────────────────────────────
# Generator emits: ⟦c001⟧...sentence...⟦/c001⟧
# Post-processor builds Dossier from spans, then strips all sentinels.
SENTINEL_OPEN = "⟦"   # ⟦
SENTINEL_CLOSE = "⟧"  # ⟧


def make_session_id() -> str:
    """CSPRNG session ID: usr_ + 22 URL-safe base62 chars (§4)."""
    alphabet = string.ascii_letters + string.digits
    return "usr_" + "".join(secrets.choice(alphabet) for _ in range(22))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Core models ───────────────────────────────────────────────────────────────

class Speaker(BaseModel):
    role: Literal["cm", "governor", "deputy_cm", "other"]
    name: Optional[str] = None
    researched_context: Optional[str] = None


class EvidenceRecord(BaseModel):
    """Per-claim evidence record (§8.2). Canonical — imported by research, generate, render, audit."""
    claim_id: str
    claim: str
    supporting_passage: str
    source_url: str
    source_tier: int          # 1 = official, 2 = press, 3 = contextual
    publisher: str
    accessed_at: datetime = Field(default_factory=_utcnow)
    confidence: Literal["high", "medium", "flagged"]


class Session(BaseModel):
    """Session data model (§5). Single contract between intake, research, generate, render."""
    session_id: str = Field(default_factory=make_session_id)
    created_at: datetime = Field(default_factory=_utcnow)
    last_activity: datetime = Field(default_factory=_utcnow)
    locale: str = "en-IN"
    doc_type: Literal["speech"] = "speech"   # M1: speech only
    speaker: Optional[Speaker] = None
    brief: str
    length_target: Literal[
        "100-150", "150-500", "500-750", "750-1250", ">1250", "as_per_content"
    ]
    uploads: List[str] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    evidence_hash: Optional[str] = None
    style_profile_ref: str = "speech_profile.json"
    audit_ref: Optional[str] = None
    status: Literal[
        "intake", "researching", "drafting", "review", "done", "error"
    ] = "intake"
    deliverable_path: Optional[str] = None
    dossier_path: Optional[str] = None
    error_message: Optional[str] = None


# ── Pipeline intermediate types ────────────────────────────────────────────────

class StyleProfile(BaseModel):
    """Cached, hash-keyed style profile (§7)."""
    category: str = "speech"
    source_hash: str = "default"
    generated_at: datetime = Field(default_factory=_utcnow)
    corpus_size: int = 0
    quality: Literal["ok", "thin", "insufficient"] = "thin"
    style_guide: str = ""
    features: dict = Field(default_factory=dict)
    exemplars: List[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Output of the research pipeline (§8)."""
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    omitted_facts: List[str] = Field(default_factory=list)
    sensitive_flags: List[str] = Field(default_factory=list)
    budget_exhausted: bool = False


class DossierEntry(BaseModel):
    """One claim entry in the Sources Dossier (§12.2)."""
    claim_id: str
    claim: str
    source_url: str
    source_tier: int
    publisher: str
    evidence_passage: str
    accessed_at: str
    confidence: Literal["high", "medium", "flagged"]


class GenerationResult(BaseModel):
    """Output of generation + sentinel processing stage."""
    clean_text: str
    raw_with_sentinels: str
    dossier_entries: List[DossierEntry] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    omitted_facts: List[str] = Field(default_factory=list)
    sensitive_flags: List[str] = Field(default_factory=list)
    used_two_pass_fallback: bool = False


class GateCheckResult(BaseModel):
    """Result of §13 gate checks, run before delivery. Audit either way."""
    passed: bool
    residual_sentinels: bool = False
    unmapped_claims: List[str] = Field(default_factory=list)
    uncovered_evidence: List[str] = Field(default_factory=list)
    length_ok: bool = True
    warnings: List[str] = Field(default_factory=list)
    blocked_tier_sources: List[str] = Field(default_factory=list)


# ── API request/response types ────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    """Frontend → API contract for session creation + generation trigger."""
    speaker_role: Literal["cm", "governor", "deputy_cm", "other"] = "cm"
    speaker_name: Optional[str] = None
    brief: str
    length_target: Literal[
        "100-150", "150-500", "500-750", "750-1250", ">1250", "as_per_content"
    ] = "500-750"
