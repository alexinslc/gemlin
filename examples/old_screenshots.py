"""Example skill: screenshots piling up on your Desktop."""
import re
import time
from contextlib import suppress
from pathlib import Path

LOOKS_LIKE = re.compile(r"^(screen ?shot|screenshot|cleanshot|capture)", re.IGNORECASE)


def old_screenshots(days: int = 7) -> dict:
    """Count screenshots older than `days` on the Desktop and in Pictures/Screenshots, with
    their total size and the oldest few. Never opens them. Use this when the user asks about
    screenshots or a cluttered Desktop."""
    home, cutoff, found = Path.home(), time.time() - days * 86400, []
    for folder in (home / "Desktop", home / "Pictures" / "Screenshots"):
        for p in folder.glob("*"):
            with suppress(OSError):
                st = p.stat()
                if p.is_file() and LOOKS_LIKE.match(p.name) and st.st_mtime < cutoff:
                    found.append((st.st_mtime, p, st.st_size))
    found.sort()
    return {"count": len(found), "total_mb": round(sum(size for _, _, size in found) / 1e6, 1),
            "oldest": [{"file": "~/" + p.relative_to(home).as_posix(), "days_old": int((time.time() - t) / 86400)}
                       for t, p, _ in found[:5]]}
