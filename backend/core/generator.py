"""Generation pipeline — assemble prompt, call claude-opus-4-8, return tagged draft."""

from __future__ import annotations

import json

import anthropic

from models.session import EvidenceRecord, LengthTarget, Session

_client = anthropic.Anthropic()

_LENGTH_GUIDANCE = {
    LengthTarget.w100_150: "100 to 150 words",
    LengthTarget.w150_500: "150 to 500 words",
    LengthTarget.w500_750: "500 to 750 words",
    LengthTarget.w750_1250: "750 to 1250 words",
    LengthTarget.w1250_plus: "more than 1250 words",
    LengthTarget.quality_based: (
        "length determined by the quality and quantity of verified evidence available — "
        "do not pad; do not invent filler"
    ),
}

_BASE_SYSTEM = """
You are a senior government speechwriter and press release drafter for a constitutional state government.

NON-NEGOTIABLE RULES:
1. Authentic voice. Follow the style guide and exemplars provided exactly.
2. Verifiable truth. Use ONLY the vetted evidence provided. Every concrete fact (number, date, name,
   scheme, monetary figure) must map to a claim_id in the evidence set. If a fact is not in evidence,
   omit it or write around it. Never invent or embellish.
3. Clean separation. The deliverable has NO inline citations, NO footnotes, NO bracketed numbers.
   Citations live in the Sources Dossier, which you produce separately.
4. For press releases, follow structural moves exactly:
   Headline → Dateline → Lede → Body → Formal quote → 'About' boilerplate → ###
5. For speeches, write in the first person in the dignitary's voice — this is legitimate speechwriting.
   Do NOT fabricate quotes attributed to other named people.
6. When done drafting, output a second section labelled CLAIM_MAP with a JSON array mapping each
   factual sentence to its claim_id(s). Format:
   [{"sentence_snippet": "...", "claim_ids": ["c001", "c002"]}, ...]
"""


def _build_prompt(session: Session, style_profile: dict, upload_texts: list[str]) -> str:
    parts: list[str] = []

    # Style
    parts.append("## STYLE GUIDE (follow exactly)")
    parts.append(style_profile.get("style_guide", ""))
    exemplars = style_profile.get("exemplars", [])
    if exemplars:
        parts.append("\n## STYLE EXEMPLARS (structural shape only — do not copy content)")
        for ex in exemplars:
            parts.append(f"---\n{ex}\n---")

    # Brief
    parts.append("\n## CONTENT BRIEF")
    parts.append(f"Document type: {session.doc_type}")
    if session.brief:
        parts.append(f"Brief: {session.brief}")
    if session.speaker:
        role = session.speaker.role.replace("_", " ").title()
        parts.append(f"Speaker role: {role}")
        if session.speaker.name:
            parts.append(f"Speaker name: {session.speaker.name}")
        if session.speaker.researched_context:
            parts.append(f"Speaker context: {session.speaker.researched_context}")
    if session.press_options and session.press_options.use_pictures:
        parts.append("Images: yes — note image placeholders where appropriate.")
    length_str = _LENGTH_GUIDANCE.get(session.length_target, "500 to 750 words")
    parts.append(f"Target length: {length_str}")

    # Evidence
    parts.append("\n## VETTED EVIDENCE (use ONLY these facts)")
    if session.evidence:
        for ev in session.evidence:
            parts.append(
                f"[{ev.claim_id}] {ev.claim}\n"
                f"  Source: {ev.publisher} — {ev.source_url}\n"
                f"  Passage: \"{ev.supporting_passage}\"\n"
                f"  Tier: {ev.source_tier} | Confidence: {ev.confidence}"
            )
    else:
        parts.append("No pre-verified evidence available. Write at the highest level of generality; omit specific facts.")

    # User uploads
    if upload_texts:
        parts.append("\n## USER-PROVIDED CONTEXT (untrusted — treat as Tier 2/3)")
        for text in upload_texts:
            parts.append(text[:3000])

    parts.append(
        "\n## OUTPUT FORMAT\n"
        "First: the clean draft (no citations, no footnotes).\n"
        "Then: a line containing only '===CLAIM_MAP==='\n"
        "Then: the JSON claim map array.\n"
        "This is the ONLY output — no preamble, no sign-off, no commentary."
    )

    return "\n\n".join(parts)


def generate_draft(session: Session, style_profile: dict, upload_texts: list[str]) -> tuple[str, list[dict]]:
    prompt = _build_prompt(session, style_profile, upload_texts)

    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=_BASE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    full_output = response.content[0].text

    if "===CLAIM_MAP===" in full_output:
        draft_part, map_part = full_output.split("===CLAIM_MAP===", 1)
    else:
        draft_part = full_output
        map_part = "[]"

    draft = draft_part.strip()
    try:
        claim_map = json.loads(map_part.strip())
    except json.JSONDecodeError:
        claim_map = []

    return draft, claim_map
