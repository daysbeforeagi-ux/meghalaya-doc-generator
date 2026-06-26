"""Research pipeline — verified sourcing with Anthropic web search tool."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic

from models.session import EvidenceRecord, Session

_client = anthropic.Anthropic()

_RESEARCH_SYSTEM = """
You are a meticulous research assistant for a government content studio.
Your job: find verified, citable evidence for every factual claim the content will make.

Source tier rules:
- Tier 1 (preferred): *.gov.in, *.nic.in, PIB, state government portals, official gazettes.
  One Tier-1 source is sufficient for a routine fact.
- Tier 2: National wire services, reputable news outlets, peer-reviewed sources, recognised institutions.
  Require ≥2 independent Tier-2 sources for any non-trivial claim.
- Tier 3 (context only): Background framing only — never the sole basis for a hard fact.
- BLOCKED: Anonymous blogs, forums, social media, AI-generated content, content farms.

For each factual need:
1. Search for it.
2. Actually open and read the page — snippets are not evidence.
3. Extract the exact supporting passage.
4. If you cannot find a real, openable source for a claim, OMIT it. Never invent citations.
5. Check recency for office-holders, statistics, or "current" facts.

Return a JSON array of evidence records. Each record:
{
  "claim_id": "c001",
  "claim": "exact claim as it will appear in the draft",
  "supporting_passage": "exact passage from the source",
  "source_url": "real, fetched URL",
  "source_tier": 1,
  "publisher": "publisher name",
  "accessed_at": "ISO timestamp",
  "confidence": "high" | "medium" | "flagged"
}

If a claim cannot be verified, exclude it entirely — do not invent a source.
Return only the JSON array, no preamble.
"""


async def run_research(session: Session) -> list[EvidenceRecord]:
    context_parts = [f"Document type: {session.doc_type}"]
    if session.brief:
        context_parts.append(f"Brief: {session.brief}")
    if session.speaker:
        role_label = session.speaker.role.replace("_", " ").title()
        context_parts.append(f"Speaker: {role_label}")
        if session.speaker.name:
            context_parts.append(f"Speaker name: {session.speaker.name}")
    if session.length_target:
        context_parts.append(f"Target length: {session.length_target} words")

    user_msg = "\n".join(context_parts)

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_RESEARCH_SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[
            {
                "role": "user",
                "content": (
                    "Please research and gather verified evidence for the following content brief.\n"
                    "Decompose the brief into atomic factual needs, then find and verify each.\n\n"
                    f"{user_msg}"
                ),
            }
        ],
    )

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text = block.text
            break

    if not raw_text.strip():
        return []

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        records_raw = json.loads(raw_text)
    except json.JSONDecodeError:
        return []

    evidence: list[EvidenceRecord] = []
    for r in records_raw:
        try:
            evidence.append(
                EvidenceRecord(
                    claim_id=r.get("claim_id", f"c{len(evidence)+1:03d}"),
                    claim=r["claim"],
                    supporting_passage=r["supporting_passage"],
                    source_url=r["source_url"],
                    source_tier=r.get("source_tier", 2),
                    publisher=r.get("publisher", "Unknown"),
                    accessed_at=datetime.now(timezone.utc),
                    confidence=r.get("confidence", "medium"),
                )
            )
        except (KeyError, ValueError):
            continue

    return evidence
