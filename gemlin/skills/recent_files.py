"""Built-in skill: files you changed recently on your Desktop, in Documents and in Downloads."""
import os
import time
from contextlib import suppress
from pathlib import Path


def recent_files(days: int = 3, top_n: int = 15) -> list:
    """List the files changed in the last few days in Desktop, Documents and Downloads,
    newest first: names, sizes and how long ago. Never opens them. Use this when the user
    asks what they worked on recently, or where a file they just saved or downloaded went."""
    home, cutoff, found = Path.home(), time.time() - days * 86400, []
    for place in ("Desktop", "Documents", "Downloads"):
        root = home / place
        for folder, subfolders, names in os.walk(root):
            subfolders[:] = [d for d in subfolders if not d.startswith(".")]
            if len(Path(folder).relative_to(root).parts) >= 3:
                subfolders[:] = []  # three folders deep is plenty
            for name in names:
                with suppress(OSError):
                    st = os.stat(os.path.join(folder, name))
                    if not name.startswith(".") and st.st_mtime >= cutoff:
                        found.append((st.st_mtime, Path(folder, name), st.st_size))
    found.sort(reverse=True)
    def ago(t):
        hours = (time.time() - t) / 3600
        return f"{int(hours * 60)} minutes ago" if hours < 1 else f"{int(hours)} hours ago" if hours < 48 else f"{int(hours // 24)} days ago"
    return [{"path": "~/" + p.relative_to(home).as_posix(), "mb": round(size / 1e6, 1), "changed": ago(t)}
            for t, p, size in found[:min(top_n, 40)]]
