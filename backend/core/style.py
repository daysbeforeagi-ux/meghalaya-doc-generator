"""Style extraction engine — extract once, reuse via hash-keyed cache."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from pypdf import PdfReader

PROFILES_DIR = Path(os.getenv("PROFILES_DIR", "/app/profiles"))
REFERENCE_DIR = Path(os.getenv("REFERENCE_DIR", "/app/reference"))
_client = anthropic.Anthropic()

CATEGORY_DIRS = {
    "speech": REFERENCE_DIR / "speeches",
    "press_release": REFERENCE_DIR / "press_releases",
}

STYLE_AXES = {
    "speech": (
        "Voice/person (1st/2nd, contractions, emotional appeal, applause lines), "
        "sentence mechanics (short punchy lines mixed with build-ups, mostly active), "
        "structure (hook → theme → tricolon/repetition → call to action), "
        "lexicon (warmth, collective 'we', aspirational verbs)."
    ),
    "press_release": (
        "Voice/person (3rd person, formal attribution, neutral register), "
        "sentence mechanics (even, declarative, inverted-pyramid front-loading), "
        "structure (headline → dateline → lede → body → formal quote → boilerplate 'About' → ### end marker), "
        "lexicon (precise nouns, dates, designations, attributions)."
    ),
}


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return path.read_text(errors="replace")


def _corpus_hash(category: str) -> str:
    folder = CATEGORY_DIRS[category]
    if not folder.exists():
        return "empty"
    entries = sorted(
        (p.name, hashlib.sha256(p.read_bytes()).hexdigest())
        for p in folder.iterdir()
        if p.is_file()
    )
    combined = json.dumps(entries, sort_keys=True)
    return "sha256:" + hashlib.sha256(combined.encode()).hexdigest()


def _profile_path(category: str) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR / f"{category}_profile.json"


def load_profile(category: str) -> dict | None:
    path = _profile_path(category)
    if not path.exists():
        return None
    current_hash = _corpus_hash(category)
    profile = json.loads(path.read_text())
    if profile.get("source_hash") == current_hash:
        return profile
    return None


def _extract_profile(category: str, texts: list[str]) -> dict:
    axes = STYLE_AXES[category]
    joined = "\n\n---\n\n".join(texts[:20])  # cap at 20 docs

    msg = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=(
            "You are a meticulous style analyst. Your job is to distil the STYLE of "
            "a writing corpus into a compact, actionable guide. You extract HOW things "
            "are written, never WHAT was said. No facts, names, or content from the "
            "corpus may appear in your output."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Analyse the following {category.replace('_', ' ')} corpus.\n"
                    f"Focus on these style axes: {axes}\n\n"
                    "Return a JSON object with these exact keys:\n"
                    '- "style_guide": markdown prose a writer can follow directly '
                    "(voice, sentence mechanics, structure, lexicon, openings, closings)\n"
                    '- "features": object with keys avg_sentence_len (int), passive_ratio (float 0-1), '
                    "reading_grade (int), person (string), rhetorical_devices (list of strings)\n"
                    '- "exemplars": list of 1-2 short structural excerpts that illustrate shape only\n\n'
                    "Return only the JSON object, no preamble.\n\n"
                    f"CORPUS:\n{joined}"
                ),
            }
        ],
    )

    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def extract_and_cache(category: str) -> dict:
    folder = CATEGORY_DIRS[category]
    texts: list[str] = []
    if folder.exists():
        for p in sorted(folder.iterdir()):
            if p.is_file():
                text = _read_file(p)
                if text.strip():
                    texts.append(text)

    if not texts:
        profile_data = {
            "style_guide": f"Default {category.replace('_', ' ')} style: formal, clear, professional.",
            "features": {
                "avg_sentence_len": 18,
                "passive_ratio": 0.1,
                "reading_grade": 10,
                "person": "third" if category == "press_release" else "first",
                "rhetorical_devices": [],
            },
            "exemplars": [],
        }
    else:
        profile_data = _extract_profile(category, texts)

    profile = {
        "category": category,
        "source_hash": _corpus_hash(category),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **profile_data,
    }

    _profile_path(category).write_text(json.dumps(profile, indent=2))
    return profile


def get_or_extract(category: str) -> dict:
    profile = load_profile(category)
    if profile is None:
        profile = extract_and_cache(category)
    return profile
