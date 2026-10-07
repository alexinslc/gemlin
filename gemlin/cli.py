"""The `gemlin` command.

  gemlin setup            check everything and save your API key
  gemlin start            wake Gemlin up on your desktop (it keeps running in the background)
  gemlin stop             put it to sleep
  gemlin restart          stop, then start (after changing its code or skills)
  gemlin status           is it awake?
  gemlin look CODE        use the look you made at gemlin.dev/create
  gemlin chat             chat in this terminal instead (with the desktop pet too, unless --no-pet)
  gemlin logs             what Gemlin has been doing
  gemlin skills           list its skills;  gemlin skills new NAME  starts one of your own
                          gemlin skills add FILE  adds a skill someone shared (it asks before loading)
  gemlin develop IDEA     build a new skill with Gemma's help: try it, change it, save it
  gemlin autostart on     wake Gemlin up whenever you log in (off turns it off)
"""
import argparse
import ast
import getpass
import json
import os
import subprocess
import sys
import time
import webbrowser
from contextlib import suppress
from pathlib import Path

import psutil

from . import __version__, paths

CREATOR = "https://gemlin.dev/create/"
KEY_PAGE = "https://aistudio.google.com/apikey"


def name():  # the name from your look, or plain Gemlin
    with suppress(OSError, ValueError, AttributeError):
        return json.loads(paths.LOOK.read_text(encoding="utf-8")).get("name") or "Gemlin"
    return "Gemlin"


def running():
    """The background Gemlin's process, if it's awake."""
    with suppress(OSError, ValueError, psutil.Error):
        proc = psutil.Process(int(paths.PID.read_text().strip()))
        if proc.is_running() and "gemlin" in " ".join(proc.cmdline()):
            return proc
    return None


def ask_yes(question, default=True):
    try:
        answer = input(f"{question} [{'Y/n' if default else 'y/N'}] ").strip().lower()
    except EOFError:
        return default
    return default if not answer else answer.startswith("y")


# ---------- setup ----------

def setup(args):
    print(f"Setting up Gemlin {__version__}\n")
    ok = check_parts()
    key = paths.api_key()
    if key and not ask_yes("  You already have an API key saved. Replace it?", default=False):
        print("  ✓ Keeping your API key")
    else:
        key = ask_key()
        if not key:
            print(f"\n  No key yet. Get a free one at {KEY_PAGE}, then run gemlin setup again.")
            return 1
    if not paths.LOOK.exists():
        print(f"\n  Make Gemlin your own (name, personality, hat, colors) at {CREATOR}")
        if ask_yes("  Open it now?"):
            webbrowser.open(CREATOR)
        print("  When you're done, run the `gemlin look ...` command it gives you.")
    print("\nAll set! Wake Gemlin up with:  gemlin start" if ok else "\nFix the ✗ above, then run gemlin setup again.")
    return 0 if ok else 1


def check_parts():
    """Make sure the pieces Gemlin needs are installed."""
    ok = sys.version_info >= (3, 10)
    print(f"  {'✓' if ok else '✗'} Python {sys.version.split()[0]}" + ("" if ok else " (Gemlin needs 3.10 or newer)"))
    window = ("AppKit", "pip install -e .  (in the gemlin folder)") if sys.platform == "darwin" else \
             ("tkinter", "sudo apt install python3-tk" if sys.platform.startswith("linux") else "reinstall Python from python.org")
    for module, label, fix in (("google.genai", "Gemini SDK", "pip install -e ."), ("psutil", "psutil", "pip install -e ."),
                               (window[0], "desktop window", window[1])):
        try:
            __import__(module)
            print(f"  ✓ {label}")
        except ImportError:
            ok = False
            print(f"  ✗ {label} is missing. To fix: {fix}")
    return ok


def ask_key():
    print(f"\n  Gemlin needs a free Gemini API key. Get one at {KEY_PAGE}")
    for _ in range(3):
        try:
            key = getpass.getpass("  Paste it here (it stays hidden): ").strip()
        except EOFError:
            return None
        if not key:
            return None
        problem = check_key(key)
        if problem is None:
            save_key(key)
            print(f"  ✓ Key works. Saved to {paths.CONFIG}")
            return key
        if problem == "offline":
            save_key(key)
            print("  ? Couldn't reach Google to test it, so it's saved untested.")
            return key
        print(f"  ✗ That key didn't work ({problem}). Try again.")
    return None


def check_key(key):
    from .core import check_key
    return check_key(key)


def save_key(key):
    paths.save_api_key(key)


# ---------- start / stop ----------

def start(args):
    if proc := running():
        print(f"{name()} is already awake (gemlin restart to restart it).")
        return 0
    no_key = not paths.api_key()
    paths.HOME.mkdir(parents=True, exist_ok=True)
    log = paths.LOG.open("a", encoding="utf-8")
    log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} gemlin start =====\n")
    log.flush()
    if sys.platform == "win32":  # its own process, with no console window
        detach = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    else:  # its own session, so closing this terminal doesn't stop it
        detach = {"start_new_session": True}
    proc = subprocess.Popen([sys.executable, "-m", "gemlin", "run", "--background"], stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, **detach)
    paths.PID.write_text(str(proc.pid))
    time.sleep(2)  # long enough to catch an early problem (a bad key, a missing piece)
    if proc.poll() is not None:
        paths.PID.unlink(missing_ok=True)
        print(f"{name()} couldn't wake up. The end of the log says:\n")
        print("\n".join(paths.LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]))
        return 1
    if no_key:
        print(f"{name()} is waking up on your desktop. It needs a free API key first, and will walk you\n"
              f"  through getting one in its window. (Or run gemlin setup.)")
    else:
        print(f"{name()} is waking up on your desktop. Say hi in its chat window!")
    print("  gemlin stop puts it to sleep · gemlin logs shows what it's doing")
    return 0


def stop(args, quiet=False):
    proc = running()
    if not proc:
        paths.PID.unlink(missing_ok=True)
        if not quiet:
            print(f"{name()} is already asleep.")
        return 0
    family = [proc, *proc.children(recursive=True)]  # Gemlin and its desktop window
    for p in family:
        with suppress(psutil.Error):
            p.terminate()
    _, alive = psutil.wait_procs(family, timeout=5)
    for p in alive:
        with suppress(psutil.Error):
            p.kill()
    paths.PID.unlink(missing_ok=True)
    if not quiet:
        print(f"{name()} went to sleep.")
    return 0


def restart(args):
    stop(args, quiet=True)
    return start(args)


def status(args):
    proc = running()
    if proc:
        awake = int(time.time() - proc.create_time())
        print(f"{name()} is awake (for {awake // 3600}h {awake % 3600 // 60}m).")
    else:
        print(f"{name()} is asleep. Wake it up with:  gemlin start")
    print(f"  API key: {'saved' if paths.api_key() else 'missing (run gemlin setup)'}")
    print(f"  Look:    {'yours, from gemlin.dev' if paths.LOOK.exists() else 'the default (make yours at ' + CREATOR + ')'}")
    if sys.platform != "win32":
        print(f"  Wakes up at login: {'yes' if autostart_file().exists() else 'no (gemlin autostart on)'}")
    return 0


def run(args):  # what `gemlin start` launches in the background
    from . import core
    try:
        core.main(desktop=True, background=args.background)
    finally:
        with suppress(OSError, ValueError):
            if int(paths.PID.read_text()) == os.getpid():
                paths.PID.unlink()


def chat(args):
    if running():
        print(f"{name()} is already awake on your desktop. Chat there, or run gemlin stop first.")
        return 1
    from . import core
    core.main(desktop=not args.no_pet)
    return 0


# ---------- look, logs, skills ----------

def look(args):
    from . import pet
    try:
        me = pet.save_look(args.code)
    except ValueError:
        print("That look code didn't work. Copy the whole command from gemlin.dev/create again.")
        return 1
    hat = me["parts"]["hat"].replace("_", " ")
    print(f"Saved! Meet {me['name']}" + (f", in a {hat}." if hat != "none" else "."))
    if running():
        print("Restarting so you can see the new look...")
        return restart(args)
    print("Wake it up with:  gemlin start")
    return 0


def logs(args):
    if not paths.LOG.exists():
        print("No log yet. Gemlin writes one when you run gemlin start.")
        return 0
    lines = paths.LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    print("\n".join(lines[-args.lines:]))
    if args.follow:
        with paths.LOG.open(encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            with suppress(KeyboardInterrupt):
                while True:
                    line = f.readline()
                    if line:
                        print(line, end="")
                    else:
                        time.sleep(0.5)
    return 0


def describe(path):
    """A skill's first docstring line, read without running the skill."""
    with suppress(OSError, SyntaxError, ValueError):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == path.stem:
                doc = " ".join((ast.get_docstring(node) or "").split())
                return doc.split(". ")[0].rstrip(".") + "." if doc else ""  # just the first sentence
    return ""


def skills(args):
    if args.action == "new":
        return new_skill(args.name)
    if args.action == "add":
        return add_skill(args.name)
    from .core import fingerprint
    trusted = set(paths.TRUSTED.read_text(encoding="utf-8").split()) if paths.TRUSTED.exists() else set()
    print("Built in (come with Gemlin):")
    for f in sorted(paths.BUILTIN_SKILLS.glob("*.py")):
        print(f"  {f.stem:22} {describe(f)}")
    yours = sorted(paths.SKILLS.glob("*.py")) if paths.SKILLS.exists() else []
    print(f"\nYours ({paths.SKILLS}):")
    for f in yours:
        approved = fingerprint(f.read_text(encoding="utf-8")) in trusted
        print(f"  {f.stem:22} {describe(f)}" + ("" if approved else "  [asks before loading]"))
    if not yours:
        print("  none yet. Ask Gemlin to learn one, or start one with:  gemlin skills new NAME")
    return 0


TEMPLATE = '''"""{name}: a skill you wrote. Gemlin loads it at start (after asking you once)."""


def {name}() -> dict:
    """Say what this does and when Gemlin should use it. Gemlin reads this to decide,
    so be specific: "Use this when the user asks about ..." """
    return {{"hello": "world"}}
'''


def add_skill(file):
    import shutil
    from pathlib import Path
    source = Path(file or "").expanduser()
    if not source.is_file() or source.suffix != ".py":
        print("Give it a skill file, like:  gemlin skills add examples/old_screenshots.py")
        return 1
    if (paths.BUILTIN_SKILLS / source.name).exists() or (paths.SKILLS / source.name).exists():
        print(f"There's already a skill called {source.stem}.")
        return 1
    paths.SKILLS.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, paths.SKILLS / source.name)
    print(f"Added {source.stem}. Run gemlin restart: Gemlin will show you its code and ask before loading it.")
    return 0


def develop(args):
    key = paths.api_key()
    if not key:
        print("Gemma needs your API key to write skills. Run:  gemlin setup")
        return 1
    from google import genai

    from . import develop as workbench
    client = genai.Client(api_key=key)
    if args.edit:
        path = paths.SKILLS / f"{args.edit}.py"
        if not path.exists():
            print(f"You don't have a skill called {args.edit} in {paths.SKILLS}.")
            return 1
        result = workbench.session(client, code=path.read_text(encoding="utf-8"))
    else:
        result = workbench.session(client, request=" ".join(args.idea) or None)
    if result == 0 and running() and ask_yes(f"Restart {name()} so it can use the new skill?"):
        restart(args)
    elif result == 0:
        print("  Gemlin will use it next time you run gemlin start.")
    return result


def new_skill(skill):
    if not skill or not skill.isidentifier():
        print("Give it a snake_case name, like:  gemlin skills new wifi_name")
        return 1
    taken = {f.stem for f in paths.BUILTIN_SKILLS.glob("*.py")}
    path = paths.SKILLS / f"{skill}.py"
    if skill in taken or path.exists():
        print(f"There's already a skill called {skill}.")
        return 1
    paths.SKILLS.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(name=skill), encoding="utf-8")
    print(f"Started {path}\nEdit it, then run gemlin restart. Gemlin will show you the code and ask before loading it.")
    return 0


# ---------- waking up at login ----------

LABEL = "dev.gemlin"


def launch_command():
    """How the computer should run `gemlin start` at login: this same Python, so it finds this Gemlin."""
    python = Path(sys.executable)
    if sys.platform == "win32" and (python.parent / "pythonw.exe").exists():
        python = python.parent / "pythonw.exe"  # no console window popping up at login
    return [str(python), "-m", "gemlin", "start"]


def autostart_file(home=None):
    home = home or Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    return home / ".config" / "autostart" / "gemlin.desktop"  # Linux; Windows uses the registry instead


def autostart(args, home=None):
    want = args.action
    if sys.platform == "win32":
        import winreg
        run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            if want == "on":
                winreg.SetValueEx(key, "Gemlin", 0, winreg.REG_SZ, subprocess.list2cmdline(launch_command()))
            elif want == "off":
                with suppress(FileNotFoundError):
                    winreg.DeleteValue(key, "Gemlin")
            try:
                winreg.QueryValueEx(key, "Gemlin")
                on = True
            except FileNotFoundError:
                on = False
    else:
        path = autostart_file(home)
        if want == "on":
            path.parent.mkdir(parents=True, exist_ok=True)
            command = launch_command()
            if sys.platform == "darwin":
                import plistlib
                path.write_bytes(plistlib.dumps({"Label": LABEL, "ProgramArguments": command, "RunAtLoad": True,
                                                 "AbandonProcessGroup": True,  # Gemlin keeps running after start exits
                                                 "StandardOutPath": str(paths.LOG), "StandardErrorPath": str(paths.LOG)}))
            else:
                path.write_text("[Desktop Entry]\nType=Application\nName=Gemlin\nComment=A tiny AI creature on your desktop\n"
                                f"Exec={subprocess.list2cmdline(command)}\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
        elif want == "off":
            path.unlink(missing_ok=True)
        on = path.exists()
    if want == "on":
        print(f"{name()} will wake up whenever you log in. (Turn it off with: gemlin autostart off)")
    elif want == "off":
        print(f"{name()} won't wake up at login anymore. (gemlin start still works any time.)")
    else:
        print(f"Wake up at login: {'on' if on else 'off'}  (gemlin autostart on / off)")
    return 0


# ---------- the command line ----------

def main(argv=None):
    sys.stdout.reconfigure(errors="replace")  # old Windows consoles and emoji
    parser = argparse.ArgumentParser(prog="gemlin", description="Gemlin: a tiny AI creature that lives on your desktop.",
                                     epilog="Make yours at https://gemlin.dev")
    parser.add_argument("--version", action="version", version=f"gemlin {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    for cmd, fn, text in (("setup", setup, "check everything and save your API key"),
                          ("start", start, "wake Gemlin up on your desktop"),
                          ("stop", stop, "put Gemlin to sleep"),
                          ("restart", restart, "stop, then start"),
                          ("status", status, "is Gemlin awake?")):
        commands.add_parser(cmd, help=text).set_defaults(fn=fn)
    p = commands.add_parser("look", help="use a look you made at gemlin.dev/create")
    p.add_argument("code")
    p.set_defaults(fn=look)
    p = commands.add_parser("chat", help="chat in this terminal (the desktop pet opens too)")
    p.add_argument("--no-pet", action="store_true", help="just the terminal")
    p.set_defaults(fn=chat)
    p = commands.add_parser("logs", help="what Gemlin has been doing")
    p.add_argument("-n", "--lines", type=int, default=40)
    p.add_argument("-f", "--follow", action="store_true", help="keep showing new lines")
    p.set_defaults(fn=logs)
    p = commands.add_parser("skills", help="list skills; gemlin skills new NAME; gemlin skills add FILE")
    p.add_argument("action", nargs="?", choices=["new", "add"])
    p.add_argument("name", nargs="?")
    p.set_defaults(fn=skills)
    p = commands.add_parser("develop", help="build a new skill with Gemma's help")
    p.add_argument("idea", nargs="*", help="what the skill should do (or leave it out and Gemlin asks)")
    p.add_argument("--edit", metavar="NAME", help="improve one of your skills instead")
    p.set_defaults(fn=develop)
    p = commands.add_parser("autostart", help="wake Gemlin up whenever you log in: on / off")
    p.add_argument("action", nargs="?", choices=["on", "off"])
    p.set_defaults(fn=autostart)
    p = commands.add_parser("run")  # used by `gemlin start`; not shown in help
    p.add_argument("--background", action="store_true")
    p.set_defaults(fn=run)
    args = parser.parse_args(argv)
    if not args.command:
        status(args)
        print("\nCommands: setup, start, stop, restart, status, look, chat, logs, skills, develop, autostart  (gemlin --help)")
        return 0
    return args.fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
