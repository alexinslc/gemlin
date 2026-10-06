# Gemlin: an AI creature that lives in your laptop and teaches itself new tricks

A tiny AI creature that lives in your laptop, powered by **Gemma 4 via the Gemini API**. It has a name and a personality, uses tools to sense your machine (Downloads, big files, busy processes, disk space), and can **write its own new tools** when you ask for something it can't do yet. You approve every change.

The default creature is **Gemlin**, a cheeky little gem-flavored creature (a play on Gemma) that loves tidy disks and teases you about your file hoarding. Change `NAME` and `PERSONA` at the top of `gemlin.py` to make your own.

Built for the **Gemlin** workshop at Hacktoberfest Hack Day Draper x AMH (Oct 16, 2026). Theme: *AI belongs to everyone.*

## Model

- **Gemma 4** (`gemma-4-26b-a4b-it`) through the Gemini API, with a free API key from Google AI Studio.
- If you hit rate limits, change one line in `gemlin.py`: `MODEL = "gemma-4-31b-it"`.
- Gemma on the Gemini API: https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
- Gemma terms of use: https://ai.google.dev/gemma/terms

Key dependencies: the official [`google-genai`](https://googleapis.github.io/python-genai/) Python SDK (chat and automatic function calling) and [`psutil`](https://pypi.org/project/psutil/) (processes, battery). Needs **Python 3.10+**.

## Setup (5 steps)

1. **Get a free API key** at https://aistudio.google.com/apikey (you need a Google account).
2. **Download this folder**: `git clone https://github.com/alexinslc/gemlin`, or use *Code → Download ZIP* and unzip it. Then `cd gemlin`.
3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt        # or: python -m pip install -r requirements.txt
   ```
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
   python gemlin.py                     # Mac: python3 gemlin.py
   ```

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
- **Skills folder:** on startup every `skills/*.py` is loaded, and the function with the same name as the file becomes a tool. `skills/battery_status.py` is an example. Skills are meant to be committed and shared.
- The SDK's **automatic function calling** does the plumbing. You pass Python functions as `tools=[...]`, and the SDK runs them when the model asks and sends the results back.

## Safety notes

- **The senses are read-only.** They report file names, sizes, and dates only. File contents are never read or sent to the model.
- **Quarantine never deletes.** It only moves a single file into `~/Gemlin_Review` after you confirm. It refuses folders and anything outside your home folder. Empty that folder yourself when you're sure.
- **Never approve code you didn't read.** `learn_skill` runs the code on your machine with your permissions. If you don't understand it, say `n`. Delete a bad skill by removing its file from `skills/`.
- **Free-tier data use:** on the Gemini API free tier, your prompts and responses may be used to improve Google products. Don't type secrets or anything private into the chat. See https://ai.google.dev/gemini-api/terms.

## Troubleshooting

- **"rate limited"**: wait about 30 seconds, or switch `MODEL` to `gemma-4-31b-it`. Each tool call counts as an extra request.
- **"No API key found"**: set `GEMINI_API_KEY` (step 4). On Windows, open a *new* terminal after `setx`.
- **API error 400 mentioning thinking**: comment out the `thinking_config=` line in `new_chat()`.
- **macOS asks for "access to files in your Documents/Desktop/Downloads folder"**: that's `find_big_files` walking your home folder. Click Allow, or say Don't Allow and it will skip those folders.

## Hack ideas

- Give your Gemlin a new name and persona (a dragon that hoards GPU memory? an anxious librarian?).
- Write a skill by hand in `skills/` (wifi info, screen time, git repos with uncommitted changes, ...).
- Ask the creature to write a skill for you, then read it carefully before saying `y`.

## License

MIT for the code in this repo, Copyright (c) 2026 Alex Lutz (see `LICENSE`). The Gemma model is covered by its own terms (linked above).
