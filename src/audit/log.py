"""
Per-generation JSONL audit log (§13).
Appended at every stage; written even when gate checks fail or pipeline errors.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import OUTPUTS_DIR


class AuditLogger:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        out_dir = OUTPUTS_DIR / session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = out_dir / "audit.jsonl"
        self._file = self.audit_path.open("a", encoding="utf-8")

    def log(self, event_type: str, **kwargs: Any) -> None:
        record = {
            "type": event_type,
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self._file.write(json.dumps(record, default=str) + "\n")
        self._file.flush()

    def log_search(self, query: str, results_count: int) -> None:
        self.log("search", query=query, results_count=results_count)

    def log_fetch(self, url: str, tier: int, success: bool) -> None:
        self.log("fetch", url=url, tier=tier, success=success)

    def log_evidence(self, claim_id: str, claim: str, source_url: str, confidence: str) -> None:
        self.log("evidence", claim_id=claim_id, claim=claim[:120], source_url=source_url, confidence=confidence)

    def log_generation(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> None:
        self.log(
            "generation",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
        )

    def log_gate_check(self, passed: bool, warnings: list[str]) -> None:
        self.log("gate_check", passed=passed, warnings=warnings)

    def log_budget(self, budget_status: dict) -> None:
        self.log("budget", **budget_status)

    def log_delivery(self, deliverable_path: str, dossier_path: str) -> None:
        self.log("delivery", deliverable_path=deliverable_path, dossier_path=dossier_path)

    def log_error(self, error: str, stage: str) -> None:
        self.log("error", error=error[:500], stage=stage)

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "AuditLogger":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
