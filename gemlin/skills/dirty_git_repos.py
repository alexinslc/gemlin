"""Built-in skill: git projects with work that isn't committed or pushed yet."""
import os
import shutil
import subprocess
import time
from pathlib import Path

SKIP = {"Library", "AppData", "node_modules", "venv", ".venv", "__pycache__"}


def dirty_git_repos() -> list:
    """Find git repositories in the home folder (up to 4 folders deep) that have changes
    not committed yet, or commits not pushed. Reports counts only. Use this when the user
    asks about unsaved work, their projects, or git. Needs git installed."""
    if not shutil.which("git"):
        return [{"error": "git is not installed"}]
    home, start, found = Path.home(), time.time(), []
    for folder, subfolders, _ in os.walk(home):
        if ".git" in subfolders:
            subfolders[:] = []  # don't look inside a repo for more repos
            result = subprocess.run(["git", "-C", folder, "status", "--porcelain", "--branch"],
                                    capture_output=True, text=True, timeout=5)
            lines = result.stdout.splitlines()
            changed = [line for line in lines[1:] if line.strip()]
            ahead = lines[0].split("ahead ")[1].split("]")[0].split(",")[0] if lines and "ahead " in lines[0] else "0"
            if changed or ahead != "0":
                found.append({"repo": "~/" + Path(folder).relative_to(home).as_posix(),
                              "changed_files": len(changed), "commits_not_pushed": int(ahead)})
            continue
        depth = len(Path(folder).relative_to(home).parts)
        subfolders[:] = [] if depth >= 4 else [d for d in subfolders if not d.startswith(".") and d not in SKIP]
        if time.time() - start > 15:
            break
    return found[:25]
