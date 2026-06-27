"""
Sentinel processing (§12.3).
Pass 1: regex extraction of ⟦cXXX⟧...⟦/cXXX⟧ pairs → build Dossier → strip.
Pass 2 fallback: content-based sentence alignment when sentinels are absent or malformed.
Validation failure does NOT block delivery — it triggers the fallback.
Only a concrete fact left completely unmapped blocks delivery (checked in gate.py).
"""
from __future__ import annotations

import re
from typing import List, Tuple

from src.intake.models import (
    DossierEntry,
    EvidenceRecord,
    GenerationResult,
    SENTINEL_OPEN,
    SENTINEL_CLOSE,
)

# Pass 1: match ⟦c001⟧...⟦/c001⟧ (non-greedy, DOTALL for multi-line sentences)
_SENTINEL_RE = re.compile(r"⟦(c\d+)⟧(.*?)⟦/\1⟧", re.DOTALL)
# Strip any remaining sentinel characters
_STRIP_RE = re.compile(r"⟦/?c\d+⟧")
# Detect residual bracket chars (used in gate.py too)
_RESIDUAL_RE = re.compile(r"[⟦⟧]")


def process_sentinels(
    raw_text: str,
    evidence: List[EvidenceRecord],
    omitted_facts: List[str],
    sensitive_flags: List[str],
) -> GenerationResult:
    """
    Extract sentinels, build Dossier entries, return clean deliverable text.
    Falls back to two-pass content alignment if no sentinels found (§12.3).
    """
    evidence_map = {e.claim_id: e for e in evidence}
    matches = _SENTINEL_RE.findall(raw_text)

    if matches:
        dossier_entries, warnings = _build_from_sentinels(matches, evidence_map)
        clean_text = _STRIP_RE.sub("", raw_text)
        used_fallback = False
    else:
        dossier_entries, warnings = _two_pass_alignment(raw_text, evidence)
        clean_text = _STRIP_RE.sub("", raw_text)
        used_fallback = True

    # Final residual check — also caught by gate.py
    if _RESIDUAL_RE.search(clean_text):
        warnings.append(
            "Residual sentinel brackets ⟦⟧ remain after strip pass — manual inspection required"
        )

    return GenerationResult(
        clean_text=clean_text.strip(),
        raw_with_sentinels=raw_text,
        dossier_entries=dossier_entries,
        warnings=warnings,
        omitted_facts=omitted_facts,
        sensitive_flags=sensitive_flags,
        used_two_pass_fallback=used_fallback,
    )


# ── Pass 1: sentinel extraction ────────────────────────────────────────────────

def _build_from_sentinels(
    matches: List[Tuple[str, str]],
    evidence_map: dict[str, EvidenceRecord],
) -> Tuple[List[DossierEntry], List[str]]:
    entries: list[DossierEntry] = []
    warnings: list[str] = []
    seen: set[str] = set()

    for claim_id, sentence in matches:
        if claim_id in seen:
            continue
        seen.add(claim_id)

        ev = evidence_map.get(claim_id)
        if ev is None:
            warnings.append(
                f"Sentinel claim_id {claim_id} has no matching evidence record — "
                "generator may have invented an ID"
            )
            continue

        entries.append(
            DossierEntry(
                claim_id=claim_id,
                claim=sentence.strip(),
                source_url=ev.source_url,
                source_tier=ev.source_tier,
                publisher=ev.publisher,
                evidence_passage=ev.supporting_passage,
                accessed_at=ev.accessed_at.isoformat(),
                confidence=ev.confidence,
            )
        )

    return entries, warnings


# ── Pass 2: content-based alignment fallback ───────────────────────────────────

def _two_pass_alignment(
    text: str,
    evidence: List[EvidenceRecord],
) -> Tuple[List[DossierEntry], List[str]]:
    warnings = [
        "No sentinels found in generator output — using two-pass content alignment fallback (§12.3). "
        "Dossier mappings are approximate; human review is essential."
    ]
    entries: list[DossierEntry] = []

    sentences = re.split(r"(?<=[.!?])\s+", text)

    for ev in evidence:
        # Match by word overlap between the claim and each sentence
        claim_words = {w.lower() for w in re.findall(r"\b\w{4,}\b", ev.claim)}
        if not claim_words:
            continue

        best_sentence: str | None = None
        best_score = 0.0

        for sentence in sentences:
            sent_words = {w.lower() for w in re.findall(r"\b\w{4,}\b", sentence)}
            if not sent_words:
                continue
            overlap = len(claim_words & sent_words) / len(claim_words)
            if overlap > best_score:
                best_score = overlap
                best_sentence = sentence

        if best_score >= 0.5 and best_sentence:
            entries.append(
                DossierEntry(
                    claim_id=ev.claim_id,
                    claim=best_sentence.strip(),
                    source_url=ev.source_url,
                    source_tier=ev.source_tier,
                    publisher=ev.publisher,
                    evidence_passage=ev.supporting_passage,
                    accessed_at=ev.accessed_at.isoformat(),
                    confidence=ev.confidence,
                )
            )
        else:
            warnings.append(
                f"Could not align {ev.claim_id} to any sentence "
                f"(best overlap {best_score:.0%}) — fact may be missing from draft"
            )

    return entries, warnings
