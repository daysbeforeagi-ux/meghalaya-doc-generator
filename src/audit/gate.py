"""
§13 pre-delivery gate checks.
Pipeline: render → gate (here) → deliver / flag → audit either way.
"""
from __future__ import annotations

import re
from typing import List

from src.intake.models import EvidenceRecord, GateCheckResult, GenerationResult

_SENTINEL_CHAR_RE = re.compile(r"[⟦⟧]")

LENGTH_RANGES: dict[str, tuple[int | None, int | None]] = {
    "100-150":      (100,  150),
    "150-500":      (150,  500),
    "500-750":      (500,  750),
    "750-1250":     (750,  1250),
    ">1250":        (1250, None),
    "as_per_content": (None, None),
}


def run_gate_checks(
    result: GenerationResult,
    evidence: List[EvidenceRecord],
    length_target: str,
) -> GateCheckResult:
    """
    Run all §13 automated gate checks.
    Must be called before delivery; result is audited regardless of outcome.
    """
    warnings = list(result.warnings)

    # 1. No residual sentinels in deliverable (§12.3)
    residual = bool(_SENTINEL_CHAR_RE.search(result.clean_text))
    if residual:
        warnings.append("Residual sentinel characters ⟦ ⟧ found in deliverable — strip failed")

    # 2. Every claim_id in dossier maps to a real evidence record
    evidence_ids = {e.claim_id for e in evidence}
    dossier_ids = {d.claim_id for d in result.dossier_entries}
    unmapped = sorted(dossier_ids - evidence_ids)
    if unmapped:
        warnings.append(f"Dossier entries have no matching evidence record: {unmapped}")

    # 3. Evidence records not referenced in dossier (informational — not a block)
    uncovered = sorted(evidence_ids - dossier_ids)
    if uncovered:
        warnings.append(f"Evidence records not cited in draft (omitted or unsupported by text): {uncovered}")

    # 4. Length sanity check
    word_count = len(result.clean_text.split())
    lo, hi = LENGTH_RANGES.get(length_target, (None, None))
    length_ok = True
    if lo is not None and word_count < lo * 0.65:
        length_ok = False
        warnings.append(
            f"Word count {word_count} is well below target '{length_target}' "
            f"(min ~{int(lo * 0.65)}). Evidence may be insufficient — see Dossier checklist."
        )
    if hi is not None and word_count > hi * 1.3:
        length_ok = False
        warnings.append(
            f"Word count {word_count} significantly exceeds target '{length_target}' (max ~{int(hi * 1.3)})."
        )

    # 5. Flagged sources — not a hard block, but surface for human review (§10.5)
    blocked_sources: list[str] = []
    for ev in evidence:
        if ev.confidence == "flagged":
            blocked_sources.append(ev.source_url)
    if blocked_sources:
        warnings.append(
            f"Flagged-confidence sources used in dossier — human review required: {blocked_sources}"
        )

    # 6. Sensitive content flags (§10.5) — always route to human review, never auto-block
    if result.sensitive_flags:
        warnings.append(
            f"Sensitive content flagged for mandatory human sign-off (§10.5): {result.sensitive_flags}"
        )

    # 7. Two-pass fallback used — note for reviewer
    if result.used_two_pass_fallback:
        warnings.append(
            "Two-pass sentinel fallback was used (§12.3) — Dossier claim-to-sentence alignment is approximate."
        )

    passed = (
        not residual
        and not unmapped
        and length_ok
    )

    return GateCheckResult(
        passed=passed,
        residual_sentinels=residual,
        unmapped_claims=unmapped,
        uncovered_evidence=uncovered,
        length_ok=length_ok,
        warnings=warnings,
        blocked_tier_sources=blocked_sources,
    )
