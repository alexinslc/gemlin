"""Built-in skill: which folders in your home folder take up the most space."""
import os
import time
from contextlib import suppress
from pathlib import Path

SKIP = {"Library", "AppData", "node_modules", "venv", "__pycache__", "Windows", "Program Files"}


def biggest_folders(top_n: int = 8) -> dict:
    """Add up the size (GB) of each folder directly inside the home folder and list the
    biggest. Use this when the user asks which folder is eating the disk or what to clean
    up first. Skips hidden and system folders; stops after 15 seconds."""
    start, sizes, complete = time.time(), {}, True
    for entry in os.scandir(Path.home()):
        if entry.name.startswith(".") or entry.name in SKIP or not entry.is_dir(follow_symlinks=False):
            continue
        total = 0
        for folder, subfolders, names in os.walk(entry.path):
            subfolders[:] = [d for d in subfolders if not d.startswith(".")]
            for name in names:
                with suppress(OSError):  # locked or vanished: skip it
                    total += os.lstat(os.path.join(folder, name)).st_size
            if time.time() - start > 15:
                complete = False
                break
        sizes[f"~/{entry.name}"] = total
        if not complete:
            break
    top = sorted(sizes.items(), key=lambda item: -item[1])[:min(top_n, 20)]
    return {"folders": [{"folder": name, "gb": round(size / 1e9, 2)} for name, size in top],
            "complete": complete}
