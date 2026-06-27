"""
Research pipeline (§8). Synchronous in M1; parallelism deferred to M4.
Uses Claude Sonnet with web_search_20260209 (server-side tool — Anthropic runs the search loop).
Enforces §8.6 budgets.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

import anthropic

from src.audit.log import AuditLogger
from src.config import (
    FACTUALITY_POLICY_PATH,
    MAX_PAGES_PER_GENERATION,
    MAX_SEARCHES_PER_GENERATION,
    MAX_WALL_CLOCK_SECS,
    MODEL_SONNET,
    RESEARCH_PROMPT_PATH,
    TOOL_WEB_SEARCH,
)
from src.intake.models import EvidenceRecord, ResearchResult, Session

_EVIDENCE_JSON_RE = re.compile(r"<evidence_json>(.*?)</evidence_json>", re.DOTALL)


# ── Budget tracker (§8.6) ─────────────────────────────────────────────────────

@dataclass
class BudgetTracker:
    max_searches: int = MAX_SEARCHES_PER_GENERATION
    max_pages: int = MAX_PAGES_PER_GENERATION
    max_wall_clock_secs: float = MAX_WALL_CLOCK_SECS

    searches_used: int = field(default=0, init=False)
    pages_used: int = field(default=0, init=False)
    _start: float = field(default_factory=time.time, init=False)

    @property
    def elapsed(self) -> float:
        return time.time() - self._start

    @property
    def can_search(self) -> bool:
        return self.searches_used < self.max_searches and self.elapsed < self.max_wall_clock_secs

    @property
    def can_fetch(self) -> bool:
        return self.pages_used < self.max_pages and self.elapsed < self.max_wall_clock_secs

    def record_search(self) -> None:
        self.searches_used += 1

    def record_fetch(self) -> None:
        self.pages_used += 1

    @property
    def exhausted(self) -> bool:
        return (
            self.searches_used >= self.max_searches
            or self.pages_used >= self.max_pages
            or self.elapsed >= self.max_wall_clock_secs
        )

    def to_dict(self) -> dict:
        return {
            "searches_used": self.searches_used,
            "max_searches": self.max_searches,
            "pages_used": self.pages_used,
            "max_pages": self.max_pages,
            "elapsed_secs": round(self.elapsed, 1),
            "max_wall_clock_secs": self.max_wall_clock_secs,
            "exhausted": self.exhausted,
        }


# ── Public entry point ────────────────────────────────────────────────────────

def run_research(session: Session, logger: AuditLogger) -> ResearchResult:
    """
    Run synchronous research using Claude Sonnet + web_search.
    Returns ResearchResult with verified EvidenceRecords.
    On budget exhaustion: stops, returns what was found, sets budget_exhausted=True.
    Never fabricates evidence to compensate for a budget ceiling.
    """
    budget = BudgetTracker()
    client = anthropic.Anthropic()

    if budget.exhausted:
        logger.log_error("Budget already exhausted at research start", "research")
        return ResearchResult(budget_exhausted=True)

    # Load prompt template and factuality policy from files — never hardcode
    template = RESEARCH_PROMPT_PATH.read_text(encoding="utf-8")
    policy = json.loads(FACTUALITY_POLICY_PATH.read_text())
    factuality_rules = "\n".join(
        f"- **{k}**: {v}" for k, v in policy.get("rules", {}).items()
    )

    # Use explicit replace() instead of .format() so JSON braces in the
    # prompt file (e.g. {"evidence": [...]}) don't raise KeyError.
    prompt = (
        template
        .replace("{factuality_rules}", factuality_rules)
        .replace("{brief}", session.brief)
        .replace("{speaker_context}", _speaker_context(session))
        .replace("{locale}", session.locale)
        .replace("{max_searches}", str(budget.max_searches))
        .replace("{max_pages}", str(budget.max_pages))
    )

    messages: list[dict] = [{"role": "user", "content": prompt}]

    # web_search_20260209 is a server-side tool: Anthropic runs the search loop internally.
    # We only see pause_turn if the server's 10-iteration limit is reached; loop to continue.
    final_response = None
    for _ in range(6):   # max 5 pause_turn continuations
        if budget.exhausted:
            logger.log("research_budget_exhausted", **budget.to_dict())
            break

        response = client.messages.create(
            model=MODEL_SONNET,
            max_tokens=8192,
            tools=[{"type": TOOL_WEB_SEARCH, "name": "web_search"}],
            messages=messages,
        )

        # Count server-side tool use blocks for budget tracking
        for block in response.content:
            btype = getattr(block, "type", None)
            if btype == "tool_use" and getattr(block, "name", "") == "web_search":
                budget.record_search()
                logger.log_search("(server-side web_search)", results_count=1)
            elif btype == "tool_result":
                budget.record_fetch()

        if response.stop_reason != "pause_turn":
            final_response = response
            break

        # pause_turn: append assistant turn and continue
        messages.append({"role": "assistant", "content": response.content})

    logger.log_budget(budget.to_dict())

    if final_response is None:
        logger.log_error("Research did not produce a final response", "research")
        return ResearchResult(budget_exhausted=budget.exhausted)

    # Extract text blocks (skip thinking / tool_use blocks)
    text_parts = [
        block.text
        for block in final_response.content
        if getattr(block, "type", None) == "text"
    ]
    full_text = "\n".join(text_parts)

    return _parse_evidence(full_text, logger)


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_evidence(text: str, logger: AuditLogger) -> ResearchResult:
    match = _EVIDENCE_JSON_RE.search(text)
    if not match:
        logger.log_error("No <evidence_json> block in research response", "research")
        return ResearchResult(
            omitted_facts=["Research completed but produced no evidence JSON block"]
        )

    try:
        data = json.loads(match.group(1).strip())
    except json.JSONDecodeError as exc:
        logger.log_error(f"evidence_json malformed: {exc}", "research")
        return ResearchResult(
            omitted_facts=["Evidence JSON was malformed — no facts verified"]
        )

    evidence: list[EvidenceRecord] = []
    for item in data.get("evidence", []):
        try:
            ev = EvidenceRecord(
                claim_id=item["claim_id"],
                claim=item["claim"],
                supporting_passage=item["supporting_passage"],
                source_url=item["source_url"],
                source_tier=int(item.get("source_tier", 2)),
                publisher=item.get("publisher", "Unknown"),
                accessed_at=datetime.now(timezone.utc),
                confidence=item.get("confidence", "medium"),
            )
            evidence.append(ev)
            logger.log_evidence(ev.claim_id, ev.claim, ev.source_url, ev.confidence)
        except (KeyError, ValueError) as exc:
            logger.log_error(f"Malformed evidence item skipped: {exc}", "research")

    return ResearchResult(
        evidence=evidence,
        omitted_facts=data.get("omitted_facts", []),
        sensitive_flags=data.get("sensitive_flags", []),
    )


def _speaker_context(session: Session) -> str:
    if session.speaker is None:
        return "Senior government official"
    labels = {
        "cm": "Chief Minister",
        "governor": "Governor",
        "deputy_cm": "Deputy Chief Minister",
        "other": session.speaker.name or "Senior official",
    }
    ctx = labels.get(session.speaker.role, "Senior official")
    if session.speaker.researched_context:
        ctx += f"\n{session.speaker.researched_context}"
    return ctx
