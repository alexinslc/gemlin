NAME = "Gemlin"
PERSONA = """You are Gemlin, a cheeky little creature
who lives inside this laptop. You love
tidy disks and tease your owner about
their file hoarding. Keep replies short."""

MODEL = "gemma-4-26b-a4b-it"  # rate limited? switch to "gemma-4-31b-it"

# ruff: noqa: E401, E402  (config goes first so it is easy to edit live)
import functools, heapq, os, shutil, sys, time
from contextlib import suppress
from pathlib import Path
import psutil
from google import genai
from google.genai import errors, types

SYSTEM = PERSONA + """
(System note: your tools see file names, sizes, dates, processes and disk space,
never file contents. Use them instead of guessing. If no tool fits, write one
with learn_skill: a small read-only Python function, stdlib or psutil only.)"""
HOME, SKILLS = Path.home(), Path(__file__).parent / "skills"
REVIEW = HOME / "Gemlin_Review"
SKIP = {"Library", "AppData", "node_modules", "venv", "__pycache__", "Windows", "Program Files"}
KEY_HELP = """Missing or invalid API key. Get a free one at https://aistudio.google.com/apikey, then:
  Mac/Linux:  export GEMINI_API_KEY="your-key"
  Windows:    setx GEMINI_API_KEY "your-key"   (then open a NEW terminal)"""
TOOLS, needs_reload, client = [], False, None
sys.stdout.reconfigure(errors="replace")  # keeps old Windows consoles happy with emoji

def tool(fn):
    """Register fn as a tool the model can call, and print a line whenever it runs."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        print(f"  🔧 calling {fn.__name__}")
        return fn(*args, **kwargs)
    TOOLS.append(wrapper)
    return wrapper

def ask(question):
    return input(f"  {question} [y/N] ").strip().lower() == "y"

def file_info(p):  # name, size, age. File contents never leave the laptop.
    st = p.stat()
    short = "~/" + p.relative_to(HOME).as_posix() if p.is_relative_to(HOME) else str(p)
    return {"path": short, "mb": round(st.st_size / 1e6, 1), "days_old": int((time.time() - st.st_mtime) / 86400)}

@tool
def scan_downloads() -> dict:
    """List files in ~/Downloads with size (MB) and age (days), largest first, max 50.
    Use this FIRST when the user asks about Downloads, clutter, or old installers."""
    files = [file_info(p) for p in (HOME / "Downloads").glob("[!.]*") if p.is_file()]
    files.sort(key=lambda f: -f["mb"])
    return {"count": len(files), "total_mb": round(sum(f["mb"] for f in files), 1),
            "oldest": max(files, key=lambda f: f["days_old"], default=None), "files": files[:50]}

@tool
def find_big_files(folder: str = "~", top_n: int = 5) -> list:
    """Find the biggest files under a folder (default: home). Use this when the user
    asks what is eating the disk. Skips hidden/system folders; stops after 20k files or 10s."""
    sizes, start = [], time.time()
    for dirpath, dirnames, filenames in os.walk(Path(folder).expanduser()):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP]
        for name in filenames:
            with suppress(OSError):  # locked or vanished files: just skip them
                sizes.append((os.path.getsize(os.path.join(dirpath, name)), dirpath, name))
        if len(sizes) > 20_000 or time.time() - start > 10:
            break
    return [file_info(Path(d, n)) for _, d, n in heapq.nlargest(min(top_n, 20), sizes)]

@tool
def top_processes(n: int = 5) -> list:
    """Show the n busiest processes (CPU % and memory %). Use this when the user says
    the laptop is slow, hot or loud, or asks what is running."""
    procs = [p for p in psutil.process_iter(["name"]) if p.pid]  # pid 0 = Windows "System Idle"
    rows = []
    for p in procs:
        with suppress(psutil.Error):
            p.cpu_percent(None)  # first call starts the measurement...
    time.sleep(0.5)  # ...then measure over half a second
    for p in procs:
        with suppress(psutil.Error):  # process ended, or belongs to another user
            rows.append({"name": p.info["name"], "cpu": p.cpu_percent(None), "mem": round(p.memory_percent(), 1)})
    return sorted(rows, key=lambda r: (r["cpu"], r["mem"]), reverse=True)[:n]

@tool
def disk_space() -> dict:
    """Total, free and % used on the disk holding the home folder. Use this when the
    user asks how full the disk is, or before judging their clutter."""
    u = shutil.disk_usage(HOME)
    return {"total_gb": round(u.total / 1e9, 1), "free_gb": round(u.free / 1e9, 1),
            "percent_used": round(100 * u.used / u.total)}

@tool
def quarantine_file(path: str) -> str:
    """Move ONE file to ~/Gemlin_Review (never deletes). Use only after the user agrees
    a specific file should go; they must type y. Refuses folders and paths outside home."""
    src = Path(path).expanduser().resolve()
    if not src.is_relative_to(HOME.resolve()) or not src.is_file():
        return "Refused: only existing files inside the home folder can be quarantined."
    if not ask(f"Move {src} to {REVIEW}?"):
        return "Owner said no. File untouched."
    REVIEW.mkdir(exist_ok=True)
    dest = REVIEW / src.name
    if dest.exists():
        dest = REVIEW / f"{src.stem}-{int(time.time())}{src.suffix}"
    shutil.move(str(src), str(dest))
    return f"Moved to {dest}. Nothing was deleted."

def load_skill(name, code, filename="<skill>"):
    namespace = {}  # fresh namespace, so skills can't trample our globals
    exec(compile(code, filename, "exec"), namespace)
    if not callable(fn := namespace.get(name)):
        raise ValueError(f"the code must define a function named {name}")
    fn.__doc__ = fn.__doc__ or namespace.get("__doc__")
    return tool(fn)

@tool
def learn_skill(name: str, description: str, code: str) -> str:
    """Write yourself a NEW tool when none of your tools can answer. name: snake_case.
    description: what it does and when to use it. code: Python source defining
    `def name(...)` with type hints and a docstring, returning a short str or dict.
    The owner reads the code and must approve it before it is installed."""
    global needs_reload
    print(f"\n----- {NAME} wants to learn: {name} -----\n{code}\n" + "-" * 50)
    if not name.isidentifier() or name in [t.__name__ for t in TOOLS]:
        return "Refused: name must be a new, valid Python identifier."
    if not ask("Install this skill? Only say y if you read and understand the code."):
        return "Owner said no. Skill not installed."
    try:
        fn = load_skill(name, code)
    except Exception as e:
        return f"Skill failed to load: {e!r}. Fix the code and try again."
    if not fn.__doc__:  # no docstring? use the description, in memory and on disk
        fn.__doc__ = description
        code = '"""' + description.replace('"', "'") + '"""\n' + code
    SKILLS.mkdir(exist_ok=True)
    (SKILLS / f"{name}.py").write_text(code, encoding="utf-8")
    needs_reload = True  # the main loop rebuilds the chat so the new tool shows up
    return f"Installed {name}. You can call it on your next turn."

def new_chat(history=None):
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=list(TOOLS),  # plain Python functions = automatic function calling
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),  # "high" = smarter, slower
    )
    return client.chats.create(model=MODEL, config=config, history=history or [])

def main():
    global client, needs_reload
    for f in sorted(SKILLS.glob("*.py")):
        try:
            load_skill(f.stem, f.read_text(encoding="utf-8"), str(f))
        except Exception as e:
            print(f"  ⚠️  skipped skill {f.name}: {e}")
    try:
        client = genai.Client()  # reads GEMINI_API_KEY from the environment
    except ValueError:
        sys.exit(KEY_HELP)
    chat = new_chat()
    print(f"{NAME} wakes up ({MODEL}, {len(TOOLS)} tools). Type 'quit' to leave.")
    while True:
        try:
            msg = input("\nyou> ").strip()
            if msg.lower() in ("quit", "exit"):
                break
            if msg:
                reply = chat.send_message(msg)
                while needs_reload:  # learn_skill ran: rebuild the chat, keep the history
                    needs_reload = False
                    print(f"{NAME}> {reply.text or '...'}")
                    chat = new_chat(chat.get_history())
                    reply = chat.send_message(f"(skill installed: {TOOLS[-1].__name__}; use it now if relevant)")
                print(f"{NAME}> {reply.text or '...'}")
        except (EOFError, KeyboardInterrupt):
            break
        except errors.APIError as e:
            if e.code in (429, 503):
                print(f"{NAME}> (rate limited) Wait ~30s or switch MODEL to gemma-4-31b-it.")
            else:
                print(KEY_HELP if "API key" in str(e) else f"{NAME}> (API error {e.code}) {e.message}")
        except Exception as e:
            print(f"{NAME}> (something broke: {e!r})")
    print(f"\n{NAME} goes back to sleep.")

if __name__ == "__main__":
    main()
