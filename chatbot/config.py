"""Tutor model settings. Everything can be overridden in a .env file (gitignored)
at the repo root or via environment variables:

    ANTHROPIC_API_KEY=sk-ant-...        # or use `ant auth login`
    TUTOR_MODEL=claude-haiku-4-5        # chosen by the user 2026-09-25
    TUTOR_EFFORT=high                   # only for models that support effort (not Haiku 4.5)
    TUTOR_THINKING_BUDGET=4000          # only for Haiku 4.5 (fixed thinking budget)
    TUTOR_MAX_TOKENS=16000
    TUTOR_BACKEND=claude-code           # "claude-code": your Claude Code (Enterprise) login, no key
                                        # "api": the Anthropic API with ANTHROPIC_API_KEY
    TUTOR_MAX_USD_PER_CALL=0.50         # claude-code backend: hard cap per call
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "answers.jsonl"


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

MODEL = os.environ.get("TUTOR_MODEL", "claude-haiku-4-5")
EFFORT = os.environ.get("TUTOR_EFFORT", "high")
MAX_TOKENS = int(os.environ.get("TUTOR_MAX_TOKENS", "16000"))
THINKING_BUDGET = int(os.environ.get("TUTOR_THINKING_BUDGET", "4000"))
BACKEND = os.environ.get("TUTOR_BACKEND", "claude-code")
MAX_USD_PER_CALL = os.environ.get("TUTOR_MAX_USD_PER_CALL", "0.50")
# Empty working folder for the claude-code backend, so no project CLAUDE.md or memory is loaded.
CLAUDE_CODE_CWD = Path.home() / ".cache" / "edexcel-maths-devtools" / "claude-code-cwd"


def is_haiku_45(model: str) -> bool:
    """Haiku 4.5 takes a fixed thinking budget, rejects `effort`, and has no server-side fallbacks."""
    return model.startswith("claude-haiku-4-5")


# Server-side refusal fallback (Claude API): if the model declines, the API re-runs the
# request on a fallback model within the same call. Used for Opus 5 / Fable 5.1, not Haiku.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
USE_FALLBACKS = os.environ.get("TUTOR_FALLBACKS", "1") != "0"


def has_credentials() -> bool:
    """True if the chosen backend can run: the claude CLI for "claude-code", or an API
    key/token for "api" (an `ant auth login` profile also works for "api")."""
    if BACKEND == "claude-code":
        import shutil
        return shutil.which("claude") is not None or (Path.home() / ".npm-global" / "bin" / "claude").exists()
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
