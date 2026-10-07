"""Where Gemlin keeps things.

Gemlin's own code, art and built-in skills live in this folder. Everything that is yours
lives in ~/.gemlin (or $GEMLIN_HOME): your API key, your look, the skills you approved
or taught it, and the log of what it's been doing.
"""
import json
import os
from contextlib import suppress
from pathlib import Path

PACKAGE = Path(__file__).parent
ART = PACKAGE / "art"                # layered sprite art (the website uses it too)
BUILTIN_SKILLS = PACKAGE / "skills"  # skills that come with Gemlin: they load without asking

HOME = Path(os.environ.get("GEMLIN_HOME") or Path.home() / ".gemlin")
CONFIG = HOME / "config.json"        # your API key, saved by `gemlin setup`
LOOK = HOME / "look.json"            # name, personality and look, saved by `gemlin look`
SKILLS = HOME / "skills"             # your skills: learned by Gemlin, written by you, or shared
TRUSTED = HOME / "trusted_skills"    # fingerprints of skill code you approved
LOG = HOME / "gemlin.log"            # what Gemlin printed while running in the background
PID = HOME / "gemlin.pid"            # which process is Gemlin, so `gemlin stop` can find it


def api_key():
    """Your Gemini API key: from GEMINI_API_KEY if it's set, otherwise the one `gemlin setup` saved."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    with suppress(OSError, ValueError, AttributeError):
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("api_key")
    return None
