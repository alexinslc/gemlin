"""Gemlin's desktop pet: a little creature that walks along the bottom of your screen.

gemlin.py starts it for you (or run `python pet.py` to just watch it walk). It builds
its sprites from the art in creator/art, recolored with your gemlin.json. Make your
look at the creator site, then run the `python gemlin.py --look ...` command it gives you.

This file decides what the pet does (the Brain). The windows are drawn by pet_mac.py
on a Mac and pet_tk.py on Windows and Linux.

gemlin.py and the pet talk with one JSON message per line:
  to the pet (stdin):    {"do": "think" | "tool" | "ask" | "idle" | "say" | "oops" | "bye", ...}
  from the pet (stdout): {"say": "something you typed into the pet's chat box"}
"""
# ruff: noqa: E401
import base64, functools, json, queue, random, re, struct, sys, threading, zlib
from contextlib import suppress
from pathlib import Path

HERE = Path(__file__).parent
ART, SETTINGS = HERE / "creator" / "art", HERE / "gemlin.json"
DEFAULTS = {
    "name": "Gemlin",
    "personality": "a cheeky little creature who lives inside this laptop. You love tidy disks "
                   "and tease your owner about their file hoarding. Keep replies short.",
    "parts": {"body": "gem", "eyes": "round", "mouth": "smile", "hat": "crown"},
    "colors": {"body": "#31d3b4", "accent": "#8e65d5", "eyes": "#0f1b27"},
    "walk": "side",
}
FIRST_FRAME = {"body": "stand", "eyes": "open", "mouth": "closed", "hat": "still"}
FALLBACK = {"walk_2": "walk_1", "walk_1": "stand", "blink": "open", "talk_1": "closed"}
KEY_COLORS = {  # the artist paints recolorable areas in these exact colors
    (255, 128, 128): ("body", "light"), (255, 0, 0): ("body", "base"), (128, 0, 0): ("body", "dark"),
    (128, 128, 255): ("accent", "light"), (0, 0, 255): ("accent", "base"), (0, 0, 128): ("accent", "dark"),
    (0, 255, 0): ("eyes", "base"),
}

# ---------- your look: gemlin.json ----------

def options(slot):
    """The art choices for one slot (body, eyes, mouth, hat): one folder each."""
    return sorted(p.name for p in (ART / slot).iterdir() if (p / f"{FIRST_FRAME[slot]}.png").exists())

def clean(raw):
    """Your settings on top of the defaults, keeping only values that make sense."""
    me = json.loads(json.dumps(DEFAULTS))  # a fresh copy
    raw = raw if isinstance(raw, dict) else {}
    for key, limit in (("name", 24), ("personality", 600)):
        if isinstance(raw.get(key), str) and raw[key].strip():
            me[key] = raw[key].strip()[:limit]
    parts = raw.get("parts") if isinstance(raw.get("parts"), dict) else {}
    for slot in me["parts"]:
        if parts.get(slot) in options(slot) or (slot == "hat" and parts.get(slot) == "none"):
            me["parts"][slot] = parts[slot]
    colors = raw.get("colors") if isinstance(raw.get("colors"), dict) else {}
    for key in me["colors"]:
        if isinstance(colors.get(key), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", colors[key]):
            me["colors"][key] = colors[key].lower()
    if raw.get("walk") in ("side", "front"):
        me["walk"] = raw["walk"]
    return me

def load_settings():
    with suppress(OSError, ValueError):
        return clean(json.loads(SETTINGS.read_text(encoding="utf-8")))
    return clean({})

def save_look(code):
    """Turn a look code from the creator site into gemlin.json. Raises ValueError if it's garbled."""
    code = code.strip()
    raw = json.loads(base64.urlsafe_b64decode(code + "=" * (-len(code) % 4)).decode("utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("not a look code")
    me = clean(raw)
    SETTINGS.write_text(json.dumps(me, indent=2) + "\n", encoding="utf-8")
    return me

# ---------- building sprites from the art ----------

@functools.lru_cache(maxsize=None)
def read_png(path):
    """Decode an 8-bit RGBA PNG into rows of (r, g, b), with None where it's see-through."""
    data, pos, idat = path.read_bytes(), 8, b""
    while pos < len(data):
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        chunk, pos = data[pos + 8:pos + 8 + size], pos + 12 + size
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            idat += chunk
    if (depth, color, interlace) != (8, 6, 0):
        raise ValueError(f"{path}: art must be 8-bit RGBA PNG")
    raw, stride, prev, rows = zlib.decompress(idat), width * 4, bytearray(width * 4), []
    for y in range(height):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):  # undo PNG's per-row filters
            a, b = (line[i - 4] if i >= 4 else 0), prev[i]
            c = prev[i - 4] if i >= 4 else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x:x + 3]) if line[x + 3] else None for x in range(0, stride, 4)])
        prev = line
    return rows

def png(rows, scale=1):
    """Encode rows of (r, g, b) / None back into PNG bytes, each pixel scale x scale big."""
    rows = [[px for px in row for _ in range(scale)] for row in rows for _ in range(scale)]
    raw = b"".join(b"\0" + b"".join(bytes((*px, 255)) if px else bytes(4) for px in row) for row in rows)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    head = struct.pack(">IIBBBBB", len(rows[0]), len(rows), 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

def shade(rgb, tone):  # the same math as the creator site, so the preview matches
    if tone == "light":
        return tuple(int(v + (255 - v) * 0.55 + 0.5) for v in rgb)
    if tone == "dark":
        return tuple(int(v * 0.5 + 0.5) for v in rgb)
    return rgb

class Sprites:
    """Stacks body, eyes, mouth and hat, recolors them, and remembers each finished frame."""

    def __init__(self, me):
        self.me, self.frames = me, {}
        rgb = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in me["colors"].items()}
        self.palette = {key: shade(rgb[slot], tone) for key, (slot, tone) in KEY_COLORS.items()}
        self.slots = [s for s in FIRST_FRAME if not (s == "hat" and me["parts"]["hat"] == "none")]
        # side view only if every chosen part has side art, since each view lines up on its own
        self.has_side = all(self.find(s, FIRST_FRAME[s], "side_") for s in self.slots)
        self.top = next((y for y, row in enumerate(self.frame()) if any(row)), 0)  # top of the hat or head

    def find(self, slot, frame, prefix=""):
        """The PNG for one layer, falling back (walk_2 -> walk_1 -> stand ...) when it's missing."""
        while frame:
            path = ART / slot / self.me["parts"][slot] / f"{prefix}{frame}.png"
            if path.exists():
                return path
            frame = FALLBACK.get(frame)
        return None

    def prefix(self, view):
        return "side_" if view == "side" and self.has_side else ""

    def steps(self, view):
        """The two body poses to alternate while walking."""
        found = self.find("body", "walk_2", self.prefix(view))
        return ["walk_1", "walk_2"] if found and found.stem.endswith("walk_2") else ["stand", "walk_1"]

    def frame(self, view="front", body="stand", eyes="open", mouth="closed", left=False):
        key = (view, body, eyes, mouth, left)
        if key not in self.frames:
            rows = [[None] * 64 for _ in range(64)]
            for slot, name in zip(self.slots, (body, eyes, mouth, "still")):
                if path := self.find(slot, name, self.prefix(view)):
                    for y, row in enumerate(read_png(path)):
                        for x, px in enumerate(row):
                            if px:
                                rows[y][x] = self.palette.get(px, px)
            self.frames[key] = [row[::-1] for row in rows] if left else rows
        return self.frames[key]

def write_manifest():
    """List the art for the creator site, which can't look inside folders: python pet.py --manifest"""
    art = {slot: {name: sorted(p.stem for p in (ART / slot / name).glob("*.png")) for name in options(slot)}
           for slot in FIRST_FRAME}
    (ART / "manifest.json").write_text(json.dumps(art, indent=1) + "\n", encoding="utf-8")

# ---------- what the pet does ----------

SCALE, SIZE, HOP = 2, 128, 12  # 64px art shown at 2x, with room above it to hop
TICK, SPEED = 40, 1.5          # 25 updates a second; pixels walked per update
INK, PAPER, MUTED = "#0f1b27", "#fff4de", "#7a7466"  # outline and cream from the art
TEXT_WIDTH, PAD, TAIL = 230, 12, 12  # speech bubble layout

def pages(text, size=170):
    """Split a reply into bubble-sized pages, at sentence breaks where possible."""
    text = re.sub(r"[*_`#]+", "", text)  # markdown marks look odd in a bubble
    out, page = [], ""
    for word in re.split(r"(?<=[.!?])\s+|\s+", text.strip()):
        if page and len(page) + len(word) >= size:
            out.append(page)
            page = ""
        page = f"{page} {word}".strip()
    return out + [page] if page else out or ["..."]

def bubble_shape(w, h):
    """Outline of a speech bubble with cut corners (pixel-art style) and a tail, y pointing down."""
    s, t = 6, min(w // 2, 40)
    return [(s, 2), (w - s, 2), (w - 2, s), (w - 2, h - s), (w - s, h), (t + 10, h), (t + 2, h + TAIL - 2),
            (t, h), (s, h), (2, h - s), (2, s)]

def above_pet(brain, w, h, tail_x=40):
    """Top-left corner for a w x h window sitting just above the pet's head (or hat)."""
    x = min(max(0, int(brain.x + SIZE / 2 - tail_x)), brain.screen_w - w)
    return x, int(brain.y + HOP + brain.art.top * SCALE - h + 2)

class Brain:
    """Decides where the pet walks, what it says and which frame shows. The window code
    (pet_mac.py or pet_tk.py) calls step() 25 times a second, then draws:
      frame, lift: the sprite to show and how many pixels it hops up
      x, y:        where the pet's window goes (top-left, screen pixels)
      bubble:      (text, footer) for the speech bubble, or None
      chatting:    whether the chat box should be open
      done:        time to close"""

    def __init__(self, me, screen_w, floor, follow):
        self.me, self.follow, self.art, self.events = me, follow, Sprites(me), queue.Queue()
        self.screen_w, self.floor = screen_w, floor - SIZE - HOP  # floor: bottom of the usable screen
        self.x, self.y, self.fall = float(random.randint(0, screen_w - SIZE)), float(self.floor), 0.0
        self.target, self.rest, self.left, self.wander = None, 50, False, True
        self.tick, self.blink_at, self.talk_until, self.hide_at, self.quit_at = 0, 60, 0, None, None
        self.mode, self.status, self.pages, self.page_count, self.seconds = "wander", None, [], 0, None
        self.grab, self.chatting, self.done, self.leaving = None, False, False, False
        self.bubble, self.frame, self.lift = None, None, 0
        if follow:
            threading.Thread(target=self.listen, daemon=True).start()
        self.say(f"Hi, I'm {me['name']}! Click me to chat.", seconds=5)

    # --- messages from gemlin.py ---
    def listen(self):  # runs in a thread; the window only changes inside step()
        for line in sys.stdin:
            with suppress(ValueError):
                self.events.put(json.loads(line))
        self.events.put({"do": "bye"})

    def handle(self, event):
        do = event.get("do") if isinstance(event, dict) else None
        if do == "think":
            self.set_mode("think", "...")
        elif do == "tool":
            self.set_mode("think", f"using {str(event.get('name', 'a tool')).replace('_', ' ')}...")
        elif do == "ask":
            self.set_mode("ask", "psst! I need a y or n in the terminal")
        elif do == "idle":
            self.set_mode("wander")
        elif do == "say":
            self.say(str(event.get("text") or "..."))
        elif do == "oops":
            self.say("oops! something went wrong. Look in the terminal.", seconds=5)
        elif do == "bye":
            self.sleep()

    def set_mode(self, mode, status=None):
        self.mode, self.status, self.pages, self.hide_at = mode, status, [], None
        self.bubble = (status, "") if status else None

    def say(self, text, seconds=None):
        self.mode, self.pages, self.seconds = "talk", pages(text), seconds
        self.page_count = len(self.pages)
        self.next_page()

    def next_page(self):
        if not self.pages:
            self.set_mode("wander")
            return
        page = self.pages.pop(0)
        done = self.page_count - len(self.pages)
        self.bubble = (page, f"{done}/{self.page_count} · click for more" if self.pages else "")
        reading = self.seconds or max(4, len(page) / 12)  # about how long it takes to read
        self.hide_at = self.tick + int(reading * 1000 / TICK)
        self.talk_until = self.tick + int(min(len(page) / 15, 4) * 1000 / TICK)

    def sleep(self):
        if not self.leaving:
            self.leaving, self.quit_at = True, self.tick + 1500 // TICK
            self.say("bye!", seconds=2)

    # --- you, with the mouse and the chat box ---
    def pick_up(self, x, y):
        self.grab = (x, y, self.x, self.y, False)

    def drag(self, x, y):
        if not self.grab:
            return
        x0, y0, px, py, moved = self.grab
        if moved or abs(x - x0) + abs(y - y0) > 4:
            self.grab = (x0, y0, px, py, True)
            self.x = min(max(0, px + x - x0), self.screen_w - SIZE)
            self.y = min(py + y - y0, self.floor)

    def drop(self):
        moved, self.grab, self.fall = self.grab and self.grab[4], None, 0
        if not moved:  # a click, not a drag
            self.chatting = not self.chatting

    def bubble_clicked(self):
        if self.mode == "talk":
            self.next_page()

    def heard(self, text):
        self.chatting = False
        text = text.strip()
        if not text:
            return
        if self.follow:
            print(json.dumps({"say": text}), flush=True)
            self.set_mode("think", "...")
        else:
            self.say("I can only chat while gemlin.py is running. Start me with: python gemlin.py")

    def toggle_wander(self):
        self.wander, self.target = not self.wander, None

    # --- 25 times a second ---
    def step(self):
        self.tick += 1
        while not self.events.empty():
            self.handle(self.events.get())
        if self.quit_at and self.tick >= self.quit_at:
            self.done = True
        if self.hide_at and self.tick >= self.hide_at:
            self.next_page()
        if self.chatting and self.mode == "talk":
            self.set_mode("wander")
        walking = False
        if self.grab:
            pass  # held by the mouse
        elif self.y < self.floor:  # dropped: fall back down
            self.fall += 1.5
            self.y = min(self.floor, self.y + self.fall)
        elif self.mode == "wander" and self.wander and not self.chatting:
            if self.target is None:
                self.rest -= 1
                if self.rest <= 0:
                    self.target = random.randint(0, self.screen_w - SIZE)
            elif abs(self.target - self.x) <= SPEED:
                self.x, self.target, self.rest = self.target, None, random.randint(60, 250)
            else:
                self.left = self.target < self.x
                self.x += -SPEED if self.left else SPEED
                walking = True
        self.pick_frame(walking)

    def pick_frame(self, walking):
        anim = self.tick // 3  # change pose about 8 times a second
        if self.tick >= self.blink_at + 4:
            self.blink_at = self.tick + random.randint(60, 150)
        eyes = "blink" if self.tick >= self.blink_at else "open"
        if walking:
            view = self.me["walk"]
            self.frame = (view, self.art.steps(view)[anim % 2], eyes, "closed", self.left)
            self.lift = 2 * SCALE * (anim % 2)  # a little bounce in each step
        else:  # standing still: turn to face you
            talking = self.mode == "talk" and self.tick < self.talk_until and anim % 2
            self.frame = ("front", "stand", eyes, "talk_1" if talking else "closed", False)
            self.lift = HOP * (anim % 4 < 2) if self.mode == "ask" else 0  # hop for attention
        if self.mode == "think" and self.status and self.tick % 12 == 0:  # make the dots dance
            dots = 1 + self.tick // 12 % 3
            self.bubble = (self.status.removesuffix("...") + "." * dots + " " * (3 - dots), "")

def run(follow):
    for stream in (sys.stdin, sys.stdout):
        with suppress(AttributeError):
            stream.reconfigure(encoding="utf-8")  # gemlin.py talks to us in UTF-8, even on Windows
    try:
        if sys.platform == "darwin":
            import pet_mac as window  # Tk can't make see-through windows on current macOS
        else:
            import pet_tk as window
    except ImportError as e:
        v = "%d.%d" % sys.version_info[:2]
        fix = {"darwin": "pip install -r requirements.txt", "linux": "sudo apt install python3-tk"}
        sys.exit(f"  (no desktop pet: {e.name} is missing. To add it: "
                 f"{fix.get(sys.platform, f'reinstall Python {v} from python.org with Tcl/Tk')})")
    window.run(load_settings(), follow)

if __name__ == "__main__":
    write_manifest() if "--manifest" in sys.argv else run(follow="--follow" in sys.argv)
