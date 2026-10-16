"""Diagnostic checks for Gemlin — a `gemlin doctor` command.

Prints clear, actionable checks and suggestions to help troubleshooting.
"""
from __future__ import annotations

import os
import sys
import textwrap

from . import paths

CHECKS = []


def _ok(msg):
    return f"  ✓ {msg}"


def _fail(msg):
    return f"  ✗ {msg}"


def _short(path):
    home = os.path.expanduser("~")
    return "~" + str(path)[len(home):] if str(path).startswith(home + os.sep) else str(path)


def doctor(args=None) -> int:
    """Run checks and print a summary. Return 0 when everything looks good, 1 otherwise."""
    problems = []
    print("Gemlin diagnostic checks\n")

    # Python version
    ok = sys.version_info >= (3, 10)
    print(_ok(f"Python {sys.version.split()[0]}") if ok else _fail(f"Python {sys.version.split()[0]} — Gemlin needs 3.10+"))
    if not ok:
        problems.append("upgrade_python")

    # Virtual environment (warn only)
    in_venv = (hasattr(sys, "real_prefix") or sys.prefix != getattr(sys, "base_prefix", sys.prefix))
    if in_venv:
        print(_ok("Running in a virtual environment"))
    else:
        print("  ? Not running inside a virtual environment. The installer at gemlin.dev sets one up for you.")

    # Required Python packages
    def check_import(module, label, fix):
        try:
            __import__(module)
            print(_ok(label))
            return True
        except Exception:
            print(_fail(f"{label} is missing — {fix}"))
            problems.append(label)
            return False

    reinstall = "run gemlin update --force (or the installer at gemlin.dev again)"
    check_import("psutil", "psutil", reinstall)
    check_import("google.genai", "Gemini SDK (google-genai)", reinstall)

    if sys.platform == "darwin":
        check_import("objc", "pyobjc (AppKit) for the see-through window on macOS", reinstall)
    elif sys.platform == "win32":
        check_import("pystray", "pystray (Windows system tray)", reinstall)
    else:
        # Linux: tkinter for the pet window
        try:
            import tkinter  # noqa: F401
            print(_ok("tkinter (desktop window)"))
        except Exception:
            print(_fail("tkinter not available — sudo apt install python3-tk (Linux)"))
            problems.append("tkinter")

    # ~/.gemlin and config
    home = paths.HOME
    if home.exists():
        try:
            perms = oct(home.stat().st_mode & 0o777)
        except Exception:
            perms = "?"
        print(_ok(f"Gemlin home: {_short(home)} ({perms})"))
    else:
        print(f"  ? No {_short(home)} yet. Gemlin makes it the first time it wakes up.")

    # Where Gemlin thinks: Google (needs a key) or this computer (needs LM Studio, Ollama, ...)
    from . import models
    local = models.source() == "local"
    if local:
        print(_ok("Thinks with Gemma on this computer (gemlin model google switches to Google)"))
    else:
        try:
            key = paths.api_key()
        except Exception:
            key = None
        if key:
            print(_ok(f"Thinks on Google; API key saved in {paths.CONFIG} (hidden)"))
        elif models.chosen():
            print(_fail("Thinks on Google, but there's no API key yet. Run: gemlin setup"))
            problems.append("no_key")
        else:
            print("  ? Not set up yet: Gemlin asks how it should think when it first wakes up (or run gemlin setup)")

    # Local model server
    try:
        apps = models.installed_apps()
        server = models.find_server(start=False)
        if server:
            model = models.pick_model(server[2])
            print(_ok(f"Local model server running: {server[0]} ({model or 'no models yet'})"))
            if local and not model:
                print(_fail(f"{server[0]} has no models. Download a Gemma model in it."))
                problems.append("no_local_model")
        elif apps:
            print(f"  ? {' and '.join(apps)} installed but not running. Gemlin starts it when it thinks on this computer.")
        elif local:
            print(_fail("Thinks on this computer, but there's no LM Studio or Ollama. Install one, or: gemlin model google"))
            problems.append("no_local_server")
        else:
            print("  ? No LM Studio or Ollama here. Install one to think on this computer (free and private).")
    except Exception:
        print("  ? Could not check for a local model server.")

    # PID / running
    try:
        from . import cli
        proc = cli.running()
        if proc:
            print(_ok(f"Gemlin process running (PID {proc.pid})"))
        else:
            print(_ok("Gemlin is asleep (wake it up with gemlin start)"))
    except Exception:
        print("  ? Couldn't determine Gemlin running status")

    # Last log lines if log exists
    if paths.LOG.exists():
        try:
            lines = paths.LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            print("\nLast log lines:")
            for line in lines[-8:]:
                print("  " + line)
        except Exception:
            print("  ? Couldn't read the log file")

    # Summary
    print("\nSummary:")
    if problems:
        print(_fail(f"{len(problems)} problem(s) found — see above for fixes"))
        print(textwrap.dedent("""
            Suggested next steps:
              - Run: gemlin setup            to pick where Gemlin thinks (and save an API key)
              - Run: gemlin update --force   if pieces are missing
            """))
        return 1
    print(_ok("No obvious problems detected."))
    return 0
