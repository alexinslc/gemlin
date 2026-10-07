# Extending Gemlin

Gemlin learns new things through **skills**: small Python files with one function. Its
docstring tells Gemlin when to use it. Here are three finished examples to read and try,
and some ideas to build yourself.

## Try an example

```bash
gemlin skills add examples/old_screenshots.py
gemlin restart
```

Gemlin shows you the code and asks before loading it (it does that for any skill that
didn't come with it). Then ask it: *"do I have old screenshots lying around?"*

| Example | Ask Gemlin |
| --- | --- |
| `old_screenshots.py` | "do I have old screenshots on my Desktop?" |
| `downloads_by_type.py` | "what kinds of files are in my Downloads?" |
| `long_running_apps.py` | "which apps have been open the longest?" |

## Build your own with Gemma

`gemlin develop` is a workbench: you describe the skill, Gemma writes it, Gemlin checks it
against the rules, and you can **try** it, ask for **changes** in plain words, and **save** it.

```bash
gemlin develop a skill that lists my oldest screenshots
```

Or, in Gemlin's chat window, type `/develop` and your idea.

Ideas to start with:

- a skill that tells me which of my apps use the most memory right now
- a skill that finds empty folders in my Documents
- a skill that lists files in Downloads I haven't opened in a year
- a skill that counts my photos by year
- a skill that tells me how full my Trash or Recycle Bin is
- a skill that finds my Python projects and when I last changed each one
- a skill that says how long until the weekend

## The rules (Gemma follows them too)

- One main function, with a snake_case name that matches the file name.
- A docstring that ends with "Use this when the user asks ...".
- Optional arguments only, with defaults.
- It only *looks*: no deleting, moving or writing files, and it never reads what's inside them.
- Standard library and `psutil` only, and it should work on Mac, Windows and Linux.

Want to improve one later? `gemlin develop --edit old_screenshots`.
