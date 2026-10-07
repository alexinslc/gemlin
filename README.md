# Gemlin: an AI creature that lives in your laptop and teaches itself new tricks

A tiny AI creature that lives in your laptop, powered by **Gemma 4 via the Gemini API**. It has a name and a personality, uses tools to sense your machine (Downloads, big files, busy processes, disk space), and can **write its own new tools** when you ask for something it can't do yet. You approve every change.

The default creature is **Gemlin**, a cheeky little gem-flavored creature (a play on Gemma) that loves tidy disks and teases you about your file hoarding. It also lives on your desktop: a little pixel-art pet walks along the bottom of your screen, answers in speech bubbles, and opens a chat box when you click it. **Design your own** (name, personality, hat, colors) at [gemlin.dev/create](https://gemlin.dev/create/), or change `NAME` and `PERSONA` at the top of `gemlin.py`.

Built for the **Gemlin** workshop at Hacktoberfest Hack Day Draper x AMH (Oct 16, 2026). Theme: *AI belongs to everyone.*

## Model

- **Gemma 4** (`gemma-4-26b-a4b-it`) through the Gemini API, with a free API key from Google AI Studio.
- If you hit rate limits, change one line in `gemlin.py`: `MODEL = "gemma-4-31b-it"`.
- Gemma on the Gemini API: https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
- Gemma terms of use: https://ai.google.dev/gemma/terms

Key dependencies: the official [`google-genai`](https://googleapis.github.io/python-genai/) Python SDK (chat and automatic function calling) and [`psutil`](https://pypi.org/project/psutil/) (processes, battery). On a Mac, [`pyobjc-framework-Cocoa`](https://pypi.org/project/pyobjc-framework-Cocoa/) draws the desktop pet's see-through window (installed automatically on Macs only). Needs **Python 3.10+**.

## Setup (5 steps)

1. **Get a free API key** at https://aistudio.google.com/apikey (you need a Google account).
2. **Download this folder**: `git clone https://github.com/alexinslc/gemlin`, or use *Code → Download ZIP* and unzip it. Then `cd gemlin`.
3. **Install the dependencies** in a virtual environment (Homebrew Python refuses a plain `pip install`):
   ```bash
   # Mac / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   ```powershell
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   Open a new terminal later? Run the `activate` line again in the gemlin folder first.
4. **Set your key** (never paste it into the code or commit it):
   ```bash
   # Mac / Linux (this terminal only)
   export GEMINI_API_KEY="your-key-here"
   ```
   ```powershell
   # Windows (saved for NEW terminals; close and reopen the terminal afterwards)
   setx GEMINI_API_KEY "your-key-here"
   ```
5. **Run it:**
   ```bash
   python gemlin.py                     # Mac: python3 gemlin.py (with the .venv activated)
   ```
   Gemlin appears in the terminal *and* on your desktop. Chat in either place. Add `--no-pet` to leave the desktop pet out.

## Make your own Gemlin

1. Open the creator at **[gemlin.dev/create](https://gemlin.dev/create/)** (or run it yourself: `python -m http.server -d site 8000`, then open http://localhost:8000/create/).
2. Pick a name, a personality, a hat and colors. Your Gemlin walks around a pretend desktop so you can see it.
3. Copy the command at the bottom (it looks like `python3 gemlin.py --look eyJuYW1l...`) and run it in your gemlin folder.

That saves your look in `gemlin.json` and starts your Gemlin. Run the command again any time to change it. Your Gemlin's name and personality in `gemlin.json` win over `NAME` and `PERSONA` in `gemlin.py`; delete `gemlin.json` to go back.

## The desktop pet

- It **walks** back and forth along the bottom of your screen, and turns to face you when it talks.
- **Replies show up in speech bubbles.** Long replies come in pages: click the bubble for the next one. The full reply is always in the terminal too.
- **Click it to chat**: type in the box, press Enter (Esc closes it). **Drag it** to move it; let go and it drops back down.
- **Right-click** for *Chat*, *Stay here* (stop walking) and *Go to sleep* (close the pet; the terminal chat keeps going).
- When Gemlin needs a `y`/`n` (quarantine, new skills), it hops and points you to the terminal. Approvals only happen in the terminal, where you can read the code.
- Run `python pet.py` to see your Gemlin walk around without chatting.

## Things to try

```
you> how bad is my Downloads folder?
you> what's eating my disk?
you> why is my laptop so loud right now?
you> move that old installer out of the way
you> how's my battery?                       (uses the example skill in skills/)
you> learn a skill that counts my Downloads files by extension
```

Every time Gemlin uses a tool you'll see a line like `🔧 calling scan_downloads`. Type `quit` or `exit` to leave.

## How it works

- **Senses (read-only):** `scan_downloads()`, `find_big_files()`, `top_processes()`, `disk_space()`. These are plain Python functions. Their docstrings tell the model *when* to use them.
- **One safe action:** `quarantine_file(path)` moves one file into `~/Gemlin_Review` after you type `y`.
- **Self-improvement:** `learn_skill(name, description, code)` lets the model write a new Python function. It prints the code, asks you `y/N`, then saves it to `skills/<name>.py` and installs it. The chat is rebuilt with the same history so the creature can use the new tool right away.
- **Skills folder:** on startup every `skills/*.py` is loaded, and the function with the same name as the file becomes a tool. `skills/battery_status.py` is an example. Skills are meant to be committed and shared, so a skill that is **new or changed since you last approved it** (for example one you just pulled from a friend) is shown and needs your `y` before it loads. Your approvals are remembered in `.trusted_skills`, which is not committed.
- **The pet** (`pet.py`) builds its sprites from the layered art in `site/art/`, recolored with your `gemlin.json`. `pet.py` decides what the pet does, `pet_mac.py` draws it on a Mac (Cocoa) and `pet_tk.py` on Windows and Linux (tkinter). `gemlin.py` and the pet talk over a pipe, one JSON line per message.
- The SDK's **automatic function calling** does the plumbing. You pass Python functions as `tools=[...]`, and the SDK runs them when the model asks and sends the results back.

## Safety notes

- **The senses are read-only.** They report file names, sizes, and dates only. File contents are never read or sent to the model.
- **Quarantine never deletes.** It only moves a single file into `~/Gemlin_Review` after you confirm. It refuses folders and anything outside your home folder. Empty that folder yourself when you're sure.
- **Never approve code you didn't read.** Skills run on your machine with your permissions. On your first run Gemlin shows you the example battery skill and asks before loading it. If you don't understand it, say `n`. Delete a bad skill by removing its file from `skills/`.
- **Free-tier data use:** on the Gemini API free tier, your prompts and responses may be used to improve Google products. Don't type secrets or anything private into the chat. See https://ai.google.dev/gemini-api/terms.

## Troubleshooting

- **"rate limited"**: wait about 30 seconds, or switch `MODEL` to `gemma-4-31b-it`. Each tool call counts as an extra request.
- **"No API key found"**: set `GEMINI_API_KEY` (step 4). On Windows, open a *new* terminal after `setx`.
- **API error 400 mentioning thinking**: comment out the `thinking_config=` line in `new_chat()`.
- **"no desktop pet: … is missing"**: on a Mac, run `pip install -r requirements.txt` again (it installs `pyobjc-framework-Cocoa`). On Linux, `sudo apt install python3-tk`. Gemlin still works in the terminal without the pet.
- **The pet has a square background on Linux**: Tk can't make see-through windows there. Mac and Windows get a see-through pet.
- **macOS asks for "access to files in your Documents/Desktop/Downloads folder"**: that's `find_big_files` walking your home folder. Click Allow, or say Don't Allow and it will skip those folders.

## Running the tests

```bash
pip install pytest
python -m pytest
```

The tests run offline (no API key needed) and use a fake home folder, so they never touch your files.

## The website (gemlin.dev)

`site/` is the whole website, as plain static files with no build step: the home page (`site/index.html`), the creator (`site/create/`), the art (`site/art/`, which the desktop pet uses too) and `site/sprites.js`, which builds sprites the same way `pet.py` does. Preview it with `python -m http.server -d site 8000`.

It's deployed to Cloudflare as a Worker with static assets (see `wrangler.jsonc`):

```bash
npx wrangler deploy
```

If you add or change art in `site/art/`, run `python pet.py --manifest` first so the site knows about it (a test checks this).

## Hack ideas

- Give your Gemlin a new name and persona at [gemlin.dev/create](https://gemlin.dev/create/) (a dragon that hoards GPU memory? an anxious librarian?).
- Draw a new hat: add a folder to `site/art/hat/` with `still.png` and `side_still.png` (64 × 64, the art's key colors), then run `python pet.py --manifest`.
- Write a skill by hand in `skills/` (wifi info, screen time, git repos with uncommitted changes, ...).
- Ask the creature to write a skill for you, then read it carefully before saying `y`.

## License

MIT for the code in this repo, Copyright (c) 2026 Alex Lutz (see `LICENSE`). The Gemma model is covered by its own terms (linked above).
