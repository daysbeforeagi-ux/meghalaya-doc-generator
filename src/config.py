from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.parent

# Export BASE_DIR so other modules (e.g. style extractor) can reference repo root

# Storage — DB_PATH is the canonical env var; ORATOR_DB_PATH kept for dev compat.
# Production: set DB_PATH=/var/lib/orator/orator.db in .env
DB_PATH = Path(
    os.getenv("DB_PATH")
    or os.getenv("ORATOR_DB_PATH")
    or str(BASE_DIR / "orator.db")
)
OUTPUTS_DIR = Path(
    os.getenv("OUTPUTS_DIR")
    or os.getenv("ORATOR_OUTPUTS_DIR")
    or str(BASE_DIR / "outputs")
)
PROFILES_DIR = BASE_DIR / "profiles"
PROMPTS_DIR = BASE_DIR / "prompts"
POLICIES_DIR = BASE_DIR / "policies"
REFERENCE_DIR = BASE_DIR / "reference"

# Model strings — pinned versioned IDs per §11.2.
# Aliases are dev-only; these strings go to the Anthropic API verbatim.
MODEL_OPUS = "claude-opus-4-8"              # final speech/press-release generation
MODEL_SONNET = "claude-sonnet-4-6"          # research, orchestration, style extraction
MODEL_HAIKU = "claude-haiku-4-5-20251001"   # classification, parsing, low-risk sub-tasks

# Server-side tool type strings
TOOL_WEB_SEARCH = "web_search_20260209"
TOOL_WEB_FETCH = "web_fetch_20260209"

# Budget caps per generation (§8.6)
MAX_SEARCHES_PER_GENERATION = int(os.getenv("MAX_SEARCHES", "20"))
MAX_PAGES_PER_GENERATION = int(os.getenv("MAX_PAGES", "30"))
MAX_WALL_CLOCK_SECS = float(os.getenv("MAX_WALL_CLOCK_SECS", "300"))

# Rate limiting (§4)
MAX_GENERATIONS_PER_SESSION = int(os.getenv("MAX_GENERATIONS_PER_SESSION", "10"))

# Versioned prompt / policy files — deployed code loads these, never CLAUDE.md
GENERATOR_PROMPT_PATH = PROMPTS_DIR / "generator_v1.md"
RESEARCH_PROMPT_PATH = PROMPTS_DIR / "research_v1.md"
FACTUALITY_POLICY_PATH = POLICIES_DIR / "factuality_v1.json"
