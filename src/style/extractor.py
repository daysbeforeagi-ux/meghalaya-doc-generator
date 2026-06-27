"""
Style engine (§7). Extract once, cache by source_hash, reuse forever.
Never runs at generation time — only on boot or when corpus changes.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import anthropic

from src.config import MODEL_SONNET, PROFILES_DIR, REFERENCE_DIR
from src.intake.models import StyleProfile

MIN_CORPUS_DOCS = 3
MIN_CORPUS_WORDS = 1500
_SUPPORTED_EXTS = {".txt", ".docx", ".pdf"}

_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def load_or_extract_profile(category: str = "speech") -> StyleProfile:
    """
    Load cached profile if corpus unchanged (§7.3), else extract from corpus.
    Falls back to the default profile shipped in profiles/ if corpus is empty.
    """
    profile_path = PROFILES_DIR / f"{category}_profile.json"
    corpus_dir = _corpus_dir(category)
    corpus_hash = _hash_corpus(corpus_dir)

    # Cache hit: stored hash matches computed hash
    if profile_path.exists():
        try:
            cached = StyleProfile.model_validate_json(profile_path.read_text())
            if cached.source_hash == corpus_hash:
                return cached
        except Exception:
            pass  # corrupt cache — re-extract

    corpus_files = _list_files(corpus_dir)

    if not corpus_files:
        # No corpus yet — load the default profile that ships with the repo
        if profile_path.exists():
            try:
                default = StyleProfile.model_validate_json(profile_path.read_text())
                return default
            except Exception:
                pass
        return _hardcoded_default(category, corpus_hash)

    profile = _extract(corpus_files, category, corpus_hash)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return profile


# ── Helpers ────────────────────────────────────────────────────────────────────

def _corpus_dir(category: str) -> Path:
    candidates = [
        REFERENCE_DIR / f"{category}es",          # reference/speeches
        REFERENCE_DIR / f"{category}s",           # reference/press_releases
        REFERENCE_DIR / category,
    ]
    for c in candidates:
        if c.exists() and any(c.iterdir()):
            return c
    return REFERENCE_DIR / category


def _hash_corpus(corpus_dir: Path) -> str:
    """SHA-256 over sorted (filename:content_hash) — deterministic (§7.3)."""
    if not corpus_dir.exists():
        return "empty"
    parts = []
    for f in sorted(corpus_dir.iterdir()):
        if f.suffix.lower() in _SUPPORTED_EXTS:
            content_hash = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            parts.append(f"{f.name}:{content_hash}")
    if not parts:
        return "empty"
    return "sha256:" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def _list_files(corpus_dir: Path) -> list[Path]:
    if not corpus_dir.exists():
        return []
    return [f for f in sorted(corpus_dir.iterdir()) if f.suffix.lower() in _SUPPORTED_EXTS]


def _extract(files: list[Path], category: str, corpus_hash: str) -> StyleProfile:
    texts: list[str] = []
    total_words = 0

    for f in files[:10]:  # cap at 10 docs for M1; large corpus → map-reduce in M3
        try:
            if f.suffix.lower() == ".txt":
                text = f.read_text(encoding="utf-8", errors="ignore")
                texts.append(text)
                total_words += len(text.split())
        except Exception:
            pass

    combined = "\n\n---\n\n".join(texts)

    quality: str
    if len(files) < MIN_CORPUS_DOCS or total_words < MIN_CORPUS_WORDS:
        quality = "thin"
    else:
        quality = "ok"

    if not combined.strip():
        return _hardcoded_default(category, corpus_hash)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL_SONNET,
        max_tokens=4096,
        messages=[{"role": "user", "content": _extraction_prompt(combined, category)}],
    )

    extracted = response.content[0].text
    match = _JSON_BLOCK_RE.search(extracted)
    if match:
        try:
            data = json.loads(match.group(1))
            return StyleProfile(
                category=category,
                source_hash=corpus_hash,
                corpus_size=len(files),
                quality=quality,
                style_guide=data.get("style_guide", ""),
                features=data.get("features", {}),
                exemplars=data.get("exemplars", []),
            )
        except Exception:
            pass

    return _hardcoded_default(category, corpus_hash)


def _extraction_prompt(corpus: str, category: str) -> str:
    return f"""Analyse the following {category} corpus and extract a reusable style profile.

CORPUS (style reference only — never copy content):
{corpus}

Extract STYLE ONLY — not content. No facts, names, figures, or phrases cross the boundary.

Output a single JSON block:
```json
{{
  "style_guide": "Detailed Markdown description covering: voice, person, rhythm, opening moves, structural pattern, rhetorical devices, tone, sentence mechanics, number conventions, and closing conventions",
  "features": {{
    "avg_sentence_len": 0,
    "passive_ratio": 0.0,
    "reading_grade": 0,
    "person": "first",
    "rhetorical_devices": []
  }},
  "exemplars": ["One or two short structural excerpts that show shape only — replace all content nouns with [TOPIC] placeholders"]
}}
```"""


def _hardcoded_default(category: str, corpus_hash: str) -> StyleProfile:
    """Minimal fallback when there is no corpus and no cached default profile."""
    return StyleProfile(
        category=category,
        source_hash=corpus_hash,
        corpus_size=0,
        quality="thin",
        style_guide=_default_style_guide(),
        features={
            "avg_sentence_len": 18,
            "passive_ratio": 0.12,
            "reading_grade": 10,
            "person": "first",
            "rhetorical_devices": ["direct address", "anaphora", "tricolon", "enumeration"],
        },
        exemplars=[
            "I am delighted to be here today for the inauguration of this [FACILITY], which represents our government's unwavering commitment to the welfare of our citizens.",
            "The journey has not been easy. But today, as we gather here, I see in your faces the hope and determination that drives us forward. Together, we will reach every home, every village, every family.",
        ],
    )


def _default_style_guide() -> str:
    return (
        "Indian government speeches follow a formal, dignified style with warmth and national purpose.\n\n"
        "**Voice:** First person ('I' for personal commitment; 'we' / 'our government' for collective action).\n\n"
        "**Opening:** Formal acknowledgments — distinguished guests, senior officers, citizens. "
        "Canonical openers: 'I am happy to inform', 'It gives me immense pleasure', 'It is my privilege to be here'.\n\n"
        "**Structure:** (1) Formal acknowledgments, (2) Context / challenge, "
        "(3) Government action, (4) Facts and impact, (5) Vision, (6) Call to action, (7) Patriotic close.\n\n"
        "**Tone:** Aspirational, people-centric, development-focused. Non-partisan. "
        "Emphasise welfare, progress, inclusivity, national interest.\n\n"
        "**Sentences:** Mix short declaratives with compound sentences. Active voice. "
        "Tricolon for emphasis ('education, health, and prosperity'). "
        "Anaphora for rhetorical build ('Today we inaugurate... today we commit... today we promise.').\n\n"
        "**Numbers:** Indian system — lakh, crore, ₹ symbol. Numerals for figures above ten.\n\n"
        "**Close:** Gratitude → reaffirm commitment → 'Jai Hind'."
    )
