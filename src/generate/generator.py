"""
Generator (§11). Calls Claude Opus with the assembled prompt.
Returns raw text containing sentinel tags (⟦cXXX⟧...⟦/cXXX⟧).
Sentinel stripping happens downstream in render/sentinel.py.
"""
from __future__ import annotations

from typing import List

import anthropic

from src.audit.log import AuditLogger
from src.config import MODEL_OPUS
from src.generate.assembler import build_generator_prompt
from src.intake.models import EvidenceRecord, Session, StyleProfile

_MAX_TOKENS = 8192


def generate_speech(
    session: Session,
    profile: StyleProfile,
    evidence: List[EvidenceRecord],
    logger: AuditLogger,
) -> str:
    """
    Call Claude Opus to draft the speech with sentinel tags (§11).
    Returns raw text including ⟦cXXX⟧...⟦/cXXX⟧ markers.

    Prompt caching (§11.4): system prompt (style guide + evidence) is marked
    ephemeral so it is reused across regenerations of the same session.
    """
    client = anthropic.Anthropic()
    system_prompt = build_generator_prompt(session, profile, evidence)

    response = client.messages.create(
        model=MODEL_OPUS,
        max_tokens=_MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    "Please draft the speech now following all instructions in the system prompt. "
                    "Remember: wrap every factual sentence with ⟦cXXX⟧...⟦/cXXX⟧ sentinel tags "
                    "where XXX exactly matches a claim_id from the evidence provided. "
                    "Output the complete speech with sentinels embedded."
                ),
            }
        ],
    )

    usage = response.usage
    logger.log_generation(
        model=MODEL_OPUS,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0),
        cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0),
    )

    # Collect only text blocks; skip thinking blocks (never expose chain-of-thought)
    text_parts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ]
    return "\n".join(text_parts)
