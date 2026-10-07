NAME = "Gemlin"
PERSONA = """You are Gemlin, a cheeky little creature
who lives inside this laptop. You love
tidy disks and tease your owner about
their file hoarding. Keep replies short."""

# Made your Gemlin on the creator site? Its name and personality (in gemlin.json) win over these.

MODEL = "gemma-4-26b-a4b-it"  # rate limited? switch to "gemma-4-31b-it"

# ruff: noqa: E401, E402  (config goes first so it is easy to edit live)
import functools, hashlib, heapq, json, os, queue, shutil, subprocess, sys, threading, time
from contextlib import suppress
from pathlib import Path
import psutil
from google import genai
from google.genai import errors, types
import pet

HERE = Path(__file__).parent
NOTE = """
(System note: your tools see file names, sizes, dates, processes and disk space,
never file contents. Use them instead of guessing. If no tool fits, write one
with learn_skill: a small read-only Python function, stdlib or psutil only.)"""
HOME, SKILLS = Path.home(), HERE / "skills"
TRUSTED = HERE / ".trusted_skills"  # fingerprints of skill code you approved (not committed)
REVIEW = HOME / "Gemlin_Review"
SKIP = {"Library", "AppData", "node_modules", "venv", "__pycache__", "Windows", "Program Files"}
KEY_HELP = """Missing or invalid API key. Get a free one at https://aistudio.google.com/apikey, then:
  Mac/Linux:  export GEMINI_API_KEY="your-key"
  Windows:    setx GEMINI_API_KEY "your-key"   (then open a NEW terminal)"""
TOOLS, needs_reload, client, pet_proc = [], False, None, None
inbox = queue.Queue()  # ("you", line) typed in the terminal, ("pet", line) typed into the pet
sys.stdout.reconfigure(errors="replace")  # keeps old Windows consoles happy with emoji

def tool(fn):
    """Register fn as a tool the model can call, and print a line whenever it runs."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        print(f"  🔧 calling {fn.__name__}")
        tell_pet(do="tool", name=fn.__name__)
        return fn(*args, **kwargs)
    TOOLS.append(wrapper)
    return wrapper

def read_terminal():  # runs in a thread, so the pet can chat while the terminal waits
    while True:
        try:
            inbox.put(("you", input()))
        except (EOFError, OSError):
            inbox.put(("you", None))
            return

def next_line(*sources):
    """Wait for the next line from the terminal ("you") and/or the pet ("pet")."""
    later = []
    try:
        while True:
            with suppress(queue.Empty):  # the timeout keeps Ctrl+C working on Windows
                source, text = inbox.get(timeout=0.2)
                if source in sources:
                    return source, text
                later.append((source, text))  # not for us right now: keep it for later
    finally:
        for item in later:
            inbox.put(item)

def start_pet():
    """Open the desktop pet (pet.py). Skip it with --no-pet."""
    global pet_proc
    if "--no-pet" in sys.argv:
        return
    pet_proc = subprocess.Popen([sys.executable, str(HERE / "pet.py"), "--follow"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True, encoding="utf-8")
    threading.Thread(target=read_pet, args=(pet_proc,), daemon=True).start()

def read_pet(proc):  # lines typed into the pet's chat box
    for line in proc.stdout:
        with suppress(ValueError, AttributeError):
            if (text := json.loads(line).get("say")) and isinstance(text, str):
                inbox.put(("pet", text))

def tell_pet(**event):  # think, tool, ask, idle, say, oops, bye
    if pet_proc and pet_proc.poll() is None:
        with suppress(OSError):  # pet was put to sleep: carry on without it
            pet_proc.stdin.write(json.dumps(event) + "\n")
            pet_proc.stdin.flush()

def ask(question):  # approvals always come from the terminal, where the code is shown
    tell_pet(do="ask")
    print(f"  {question} [y/N] ", end="", flush=True)
    _, answer = next_line("you")
    tell_pet(do="idle")
    return (answer or "").strip().lower() == "y"

def file_info(p):  # name, size, age. File contents never leave the laptop.
    st = p.stat()
    short = "~/" + p.relative_to(HOME).as_posix() if p.is_relative_to(HOME) else str(p)
    return {"path": short, "mb": round(st.st_size / 1e6, 1), "days_old": int((time.time() - st.st_mtime) / 86400)}

def file_infos(paths):  # file_info for each path, skipping files that vanish or are locked
    infos = []
    for p in paths:
        with suppress(OSError):
            infos.append(file_info(p))
    return infos

@tool
def scan_downloads() -> dict:
    """List files in ~/Downloads with size (MB) and age (days), largest first, max 50.
    Use this FIRST when the user asks about Downloads, clutter, or old installers."""
    files = file_infos(p for p in (HOME / "Downloads").glob("[!.]*") if p.is_file())
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
    return file_infos(Path(d, n) for _, d, n in heapq.nlargest(min(top_n, 20), sizes))

@tool
def top_processes(n: int = 5) -> list:
    """Show the n busiest processes (% of the whole machine's CPU, and memory %). Use this
    when the user says the laptop is slow, hot or loud, or asks what is running."""
    procs = [p for p in psutil.process_iter(["name"]) if p.pid]  # pid 0 = Windows "System Idle"
    rows, cores = [], psutil.cpu_count() or 1
    for p in procs:
        with suppress(psutil.Error):
            p.cpu_percent(None)  # first call starts the measurement...
    time.sleep(0.5)  # ...then measure over half a second
    for p in procs:
        with suppress(psutil.Error):  # process ended, or belongs to another user
            rows.append({"name": p.info["name"], "cpu": round(p.cpu_percent(None) / cores, 1), "mem": round(p.memory_percent(), 1)})
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

def fingerprint(code):
    return hashlib.sha256(code.encode()).hexdigest()

def trust(code):  # remember approved code, so it loads without asking next time
    with TRUSTED.open("a", encoding="utf-8") as f:
        f.write(fingerprint(code) + "\n")

def show_code(title, code):
    print(f"\n----- {title} -----\n{code}\n" + "-" * 50)

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
    show_code(f"{NAME} wants to learn: {name}", code)
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
    trust(code)
    needs_reload = True  # the main loop rebuilds the chat so the new tool shows up
    return f"Installed {name}. You can call it on your next turn."

def new_chat(history=None):
    config = types.GenerateContentConfig(
        system_instruction=PERSONA + NOTE,
        tools=list(TOOLS),  # plain Python functions = automatic function calling
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),  # "high" = smarter, slower
    )
    return client.chats.create(model=MODEL, config=config, history=history or [])

def main():
    global client, needs_reload, NAME, PERSONA
    if "--look" in sys.argv:  # the command from the creator site
        try:
            pet.save_look(sys.argv[sys.argv.index("--look") + 1])
        except (IndexError, ValueError):
            sys.exit("That look code didn't work. Copy the whole command from the creator site again.")
        print("  Saved your new look to gemlin.json.")
    if pet.SETTINGS.exists():  # made with the creator site
        me = pet.load_settings()
        NAME, PERSONA = me["name"], f"You are {me['name']}, {me['personality']}"
    try:
        client = genai.Client()  # reads GEMINI_API_KEY from the environment
    except ValueError:
        sys.exit(KEY_HELP + "\n(To see your Gemlin walk around without chatting: python pet.py)")
    threading.Thread(target=read_terminal, daemon=True).start()
    start_pet()
    trusted = set(TRUSTED.read_text(encoding="utf-8").split()) if TRUSTED.exists() else set()
    for f in sorted(SKILLS.glob("*.py")):
        code = f.read_text(encoding="utf-8")
        if fingerprint(code) not in trusted:  # new or changed since you last approved it
            show_code(f"new skill: {f.name}", code)
            if not ask("Load this skill? Only say y if you read and understand the code."):
                print(f"  skipped skill {f.name} (it will ask again next time)")
                continue
            trust(code)
        try:
            load_skill(f.stem, code, str(f))
        except Exception as e:
            print(f"  ⚠️  skipped skill {f.name}: {e}")
    chat = new_chat()
    print(f"{NAME} wakes up ({MODEL}, {len(TOOLS)} tools). Type 'quit' to leave."
          + (f" You can also click {NAME} on your desktop to chat." if pet_proc else ""))
    while True:
        try:
            print("\nyou> ", end="", flush=True)
            source, msg = next_line("you", "pet")
            if msg is None:
                break
            if source == "pet":
                print(f"{msg}   (typed into {NAME})")
            msg = msg.strip()
            if msg.lower() in ("quit", "exit"):
                break
            if msg:
                tell_pet(do="think")
                reply = chat.send_message(msg)
                while needs_reload:  # learn_skill ran: rebuild the chat, keep the history
                    needs_reload = False
                    print(f"{NAME}> {reply.text or '...'}")
                    chat = new_chat(chat.get_history())
                    reply = chat.send_message(f"(skill installed: {TOOLS[-1].__name__}; use it now if relevant)")
                print(f"{NAME}> {reply.text or '...'}")
                tell_pet(do="say", text=reply.text or "...")
        except (EOFError, KeyboardInterrupt):
            break
        except errors.APIError as e:
            tell_pet(do="oops")
            if e.code in (429, 503):
                print(f"{NAME}> (rate limited) Wait ~30s or switch MODEL to gemma-4-31b-it.")
            else:
                print(KEY_HELP if "API key" in str(e) else f"{NAME}> (API error {e.code}) {e.message}")
        except Exception as e:
            tell_pet(do="oops")
            print(f"{NAME}> (something broke: {e!r})")
    tell_pet(do="bye")
    print(f"\n{NAME} goes back to sleep.")

if __name__ == "__main__":
    main()
