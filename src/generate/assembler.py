"""
Prompt assembler (§11.1).
Loads versioned templates from prompts/ and policy from policies/ — never hardcodes.
All other modules that need these rules import from here.
"""
from __future__ import annotations

import json
from typing import List

from src.config import FACTUALITY_POLICY_PATH, GENERATOR_PROMPT_PATH
from src.intake.models import EvidenceRecord, Session, Speaker, StyleProfile


def load_factuality_rules() -> str:
    """Load the §10 contract from policies/factuality_v1.json as formatted text."""
    policy = json.loads(FACTUALITY_POLICY_PATH.read_text(encoding="utf-8"))
    return "\n".join(f"- **{k}**: {v}" for k, v in policy.get("rules", {}).items())


def build_generator_prompt(
    session: Session,
    profile: StyleProfile,
    evidence: List[EvidenceRecord],
) -> str:
    """
    Assemble the generator system prompt from the versioned template (§11.1).
    Prompt-caching is applied by the caller on this block.
    """
    template = GENERATOR_PROMPT_PATH.read_text(encoding="utf-8")

    return template.format(
        factuality_rules=load_factuality_rules(),
        style_guide=profile.style_guide or "(No style guide available — use standard Indian government speech style.)",
        exemplars="\n\n".join(f'"{e}"' for e in profile.exemplars) or "(No exemplars available.)",
        doc_type=session.doc_type,
        speaker=_format_speaker(session.speaker),
        brief=session.brief,
        length_target=session.length_target,
        locale=session.locale,
        evidence_block=_format_evidence(evidence),
    )


# ── Formatters ────────────────────────────────────────────────────────────────

def _format_speaker(speaker: Speaker | None) -> str:
    if speaker is None:
        return "A senior government official"
    labels = {
        "cm": "Honourable Chief Minister",
        "governor": "Honourable Governor",
        "deputy_cm": "Honourable Deputy Chief Minister",
        "other": speaker.name or "A senior government official",
    }
    label = labels.get(speaker.role, "Honourable official")
    if speaker.researched_context:
        return f"{label}\n\nContext: {speaker.researched_context}"
    return label


def _format_evidence(evidence: List[EvidenceRecord]) -> str:
    if not evidence:
        return (
            "(No verified evidence available. "
            "Omit all concrete factual claims from the speech.)"
        )

    tier_labels = {1: "Official (Tier 1)", 2: "Established Press (Tier 2)", 3: "Contextual (Tier 3)"}
    blocks = []
    for ev in evidence:
        tier = tier_labels.get(ev.source_tier, f"Tier {ev.source_tier}")
        blocks.append(
            f"[{ev.claim_id}]\n"
            f"  Claim:     {ev.claim}\n"
            f'  Evidence:  "{ev.supporting_passage}"\n'
            f"  Source:    {ev.publisher} ({tier}) — {ev.source_url}\n"
            f"  Confidence: {ev.confidence}"
        )
    return "\n\n".join(blocks)
