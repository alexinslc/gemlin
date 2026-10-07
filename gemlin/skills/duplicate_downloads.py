"""Built-in skill: likely duplicate files in Downloads (the same thing downloaded twice)."""
import re
from contextlib import suppress
from pathlib import Path

COPY_MARK = re.compile(r"( ?\(\d+\)| copy( \d+)?)$")  # "report (1).pdf", "photo copy 2.jpg"


def duplicate_downloads() -> list:
    """Find likely duplicates in ~/Downloads: files with the same size and the same name
    apart from copy marks like " (1)" or " copy". Never opens the files. Use this when the
    user asks about duplicates, re-downloads, or what is safe to clean out of Downloads."""
    groups = {}
    for p in (Path.home() / "Downloads").glob("[!.]*"):
        with suppress(OSError):
            if p.is_file():
                key = (COPY_MARK.sub("", p.stem.lower()), p.suffix.lower(), p.stat().st_size)
                groups.setdefault(key, []).append(p.name)
    dupes = [{"files": sorted(names), "mb_each": round(key[2] / 1e6, 1),
              "mb_wasted": round(key[2] * (len(names) - 1) / 1e6, 1)}
             for key, names in groups.items() if len(names) > 1]
    return sorted(dupes, key=lambda d: -d["mb_wasted"])[:20]
