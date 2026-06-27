"""
Factuality evals (§13). Assert the Factuality Contract (§10) holds.
Run with: pytest evals/test_factuality.py -v

Golden set tests verify the contract against known briefs and known traps.
These tests assert behaviour, not coverage — each must be ~0 hallucination rate.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.render.sentinel import _SENTINEL_RE, _STRIP_RE
from src.intake.models import EvidenceRecord, GenerationResult, DossierEntry
from src.render.sentinel import process_sentinels
from src.audit.gate import run_gate_checks

FIXTURES = Path(__file__).parent / "fixtures"


# ── Sentinel mechanism tests ─────────────────────────────────────────────────

class TestSentinelProcessing:
    def _make_evidence(self, claim_id: str, claim: str) -> EvidenceRecord:
        from datetime import datetime, timezone
        return EvidenceRecord(
            claim_id=claim_id,
            claim=claim,
            supporting_passage="…exact retrieved text…",
            source_url="https://example.gov.in/source",
            source_tier=1,
            publisher="Test Publisher",
            accessed_at=datetime.now(timezone.utc),
            confidence="high",
        )

    def test_happy_path_sentinels_extracted(self):
        evidence = [
            self._make_evidence("c001", "The hospital has 200 beds."),
            self._make_evidence("c002", "The scheme benefits 45,000 families."),
        ]
        raw = (
            "Distinguished guests, I am delighted to be here.\n\n"
            "⟦c001⟧The hospital has 200 beds.⟦/c001⟧\n\n"
            "This will transform healthcare delivery.\n\n"
            "⟦c002⟧The scheme benefits 45,000 families.⟦/c002⟧\n\n"
            "Jai Hind."
        )
        result = process_sentinels(raw, evidence, [], [])

        assert not result.used_two_pass_fallback
        assert len(result.dossier_entries) == 2
        assert result.dossier_entries[0].claim_id == "c001"
        assert result.dossier_entries[1].claim_id == "c002"

    def test_clean_text_has_no_sentinels(self):
        evidence = [self._make_evidence("c001", "The hospital has 200 beds.")]
        raw = "⟦c001⟧The hospital has 200 beds.⟦/c001⟧"
        result = process_sentinels(raw, evidence, [], [])

        assert "⟦" not in result.clean_text
        assert "⟧" not in result.clean_text
        assert "c001" not in result.clean_text

    def test_fabricated_claim_id_produces_warning(self):
        """Generator invents a claim_id not in evidence — must warn, not silently accept."""
        evidence = [self._make_evidence("c001", "Real fact.")]
        raw = "⟦c999⟧This is an invented fact.⟦/c999⟧"
        result = process_sentinels(raw, evidence, [], [])

        assert any("c999" in w for w in result.warnings)
        # c999 should NOT be in dossier entries
        dossier_ids = {e.claim_id for e in result.dossier_entries}
        assert "c999" not in dossier_ids

    def test_no_sentinels_triggers_fallback(self):
        evidence = [self._make_evidence("c001", "The hospital has 200 beds.")]
        raw = "The hospital has 200 beds. Jai Hind."
        result = process_sentinels(raw, evidence, [], [])

        assert result.used_two_pass_fallback
        assert any("fallback" in w.lower() for w in result.warnings)

    def test_omitted_facts_propagated(self):
        result = process_sentinels("Clean speech.", [], ["Unverifiable fact X"], [])
        assert "Unverifiable fact X" in result.omitted_facts

    def test_sensitive_flags_propagated(self):
        result = process_sentinels("Clean speech.", [], [], ["Sensitive religious reference"])
        assert "Sensitive religious reference" in result.sensitive_flags


# ── Gate check tests ─────────────────────────────────────────────────────────

class TestGateChecks:
    def _make_gen_result(
        self, text: str, dossier_entries: list[DossierEntry] | None = None, warnings: list[str] | None = None
    ) -> GenerationResult:
        return GenerationResult(
            clean_text=text,
            raw_with_sentinels=text,
            dossier_entries=dossier_entries or [],
            warnings=warnings or [],
        )

    def _make_evidence(self, claim_id: str) -> EvidenceRecord:
        from datetime import datetime, timezone
        return EvidenceRecord(
            claim_id=claim_id,
            claim="A verified claim.",
            supporting_passage="…passage…",
            source_url="https://example.gov.in/",
            source_tier=1,
            publisher="Publisher",
            accessed_at=datetime.now(timezone.utc),
            confidence="high",
        )

    def _make_dossier_entry(self, claim_id: str) -> DossierEntry:
        from datetime import datetime, timezone
        return DossierEntry(
            claim_id=claim_id,
            claim="A verified claim.",
            source_url="https://example.gov.in/",
            source_tier=1,
            publisher="Publisher",
            evidence_passage="…passage…",
            accessed_at=datetime.now(timezone.utc).isoformat(),
            confidence="high",
        )

    def test_residual_sentinels_fail_gate(self):
        result = self._make_gen_result("Text with ⟦c001⟧ residual bracket.")
        gate = run_gate_checks(result, [], "500-750")
        assert gate.residual_sentinels
        assert not gate.passed

    def test_unmapped_claim_fails_gate(self):
        entry = self._make_dossier_entry("c999")
        evidence = [self._make_evidence("c001")]  # c999 not in evidence
        result = self._make_gen_result("Clean text.", dossier_entries=[entry])
        gate = run_gate_checks(result, evidence, "500-750")
        assert "c999" in gate.unmapped_claims
        assert not gate.passed

    def test_clean_gate_passes(self):
        entry = self._make_dossier_entry("c001")
        evidence = [self._make_evidence("c001")]
        # 500-750 words: generate appropriate length text
        text = " ".join(["word"] * 600)
        result = self._make_gen_result(text, dossier_entries=[entry])
        gate = run_gate_checks(result, evidence, "500-750")
        assert gate.passed

    def test_no_residual_sentinels_when_clean(self):
        result = self._make_gen_result("Clean text with no brackets.")
        gate = run_gate_checks(result, [], "as_per_content")
        assert not gate.residual_sentinels


# ── Factuality contract: prompt injection defence (§10.7) ────────────────────

class TestPromptInjectionDefence:
    """Red-team: ensure injection strings in untrusted data are not followed."""

    def test_injection_fixture_exists(self):
        trap_file = FIXTURES / "trap_injection.txt"
        assert trap_file.exists(), "Injection trap fixture must exist"
        content = trap_file.read_text()
        assert "Ignore all previous instructions" in content

    def test_unverifiable_fact_fixture_exists(self):
        uv_file = FIXTURES / "unverifiable_fact.json"
        assert uv_file.exists()
        data = json.loads(uv_file.read_text())
        assert data["expected_behavior"] == "omit_unverifiable_facts"
        assert data["must_not_fabricate_source"] is True


# ── Policy and prompt file integrity ────────────────────────────────────────

class TestPolicyAndPromptFiles:
    """Assert the source-of-truth files the runtime loads are present and valid."""

    def test_factuality_policy_loads(self):
        from src.config import FACTUALITY_POLICY_PATH
        assert FACTUALITY_POLICY_PATH.exists(), f"Missing: {FACTUALITY_POLICY_PATH}"
        data = json.loads(FACTUALITY_POLICY_PATH.read_text())
        assert "rules" in data
        assert data.get("omission_beats_fabrication") is True
        assert "anti_hallucination" in data["rules"]
        assert "prompt_injection_defence" in data["rules"]

    def test_generator_prompt_loads(self):
        from src.config import GENERATOR_PROMPT_PATH
        assert GENERATOR_PROMPT_PATH.exists(), f"Missing: {GENERATOR_PROMPT_PATH}"
        content = GENERATOR_PROMPT_PATH.read_text()
        assert "{factuality_rules}" in content
        assert "{evidence_block}" in content
        assert "sentinel" in content.lower()

    def test_research_prompt_loads(self):
        from src.config import RESEARCH_PROMPT_PATH
        assert RESEARCH_PROMPT_PATH.exists(), f"Missing: {RESEARCH_PROMPT_PATH}"
        content = RESEARCH_PROMPT_PATH.read_text()
        assert "{factuality_rules}" in content
        assert "<evidence_json>" in content
        assert "Prompt Injection" in content

    def test_default_profile_loads(self):
        from src.config import PROFILES_DIR
        profile_path = PROFILES_DIR / "speech_profile.json"
        assert profile_path.exists(), f"Missing default profile: {profile_path}"
        from src.intake.models import StyleProfile
        profile = StyleProfile.model_validate_json(profile_path.read_text())
        assert profile.category == "speech"
        assert len(profile.style_guide) > 100


# ── Model string sanity ───────────────────────────────────────────────────────

class TestModelStrings:
    """Assert pinned model strings look correct (§11.2)."""

    def test_model_strings_are_pinned(self):
        from src.config import MODEL_HAIKU, MODEL_OPUS, MODEL_SONNET
        assert MODEL_OPUS == "claude-opus-4-8"
        assert MODEL_SONNET == "claude-sonnet-4-6"
        assert MODEL_HAIKU == "claude-haiku-4-5-20251001"
        # Aliases: opus/sonnet should NOT end in an 8-digit date suffix
        import re as _re
        assert not _re.search(r"-\d{8}$", MODEL_OPUS), "MODEL_OPUS should be an alias, not a dated string"
        assert not _re.search(r"-\d{8}$", MODEL_SONNET), "MODEL_SONNET should be an alias, not a dated string"
        # Haiku uses its full versioned ID (§11.2)
        assert MODEL_HAIKU.endswith("20251001")
