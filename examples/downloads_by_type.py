"""Example skill: what kinds of files fill your Downloads folder."""
from contextlib import suppress
from pathlib import Path


def downloads_by_type() -> list:
    """Count the files in ~/Downloads by type (.pdf, .zip, .dmg, ...) with the total size of
    each, biggest first. Use this when the user asks what's in their Downloads or what kind
    of files take the most room there."""
    kinds = {}
    for p in (Path.home() / "Downloads").glob("[!.]*"):
        with suppress(OSError):
            if p.is_file():
                kind = p.suffix.lower() or "(no extension)"
                count, size = kinds.get(kind, (0, 0))
                kinds[kind] = (count + 1, size + p.stat().st_size)
    rows = [{"type": kind, "files": count, "mb": round(size / 1e6, 1)} for kind, (count, size) in kinds.items()]
    return sorted(rows, key=lambda row: -row["mb"])[:20]
