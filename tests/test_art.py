"""Checks every art file against the rules the pet's code relies on (see docs/art-requests/).

Whoever adds art runs:  python -m pytest tests/test_art.py
A failure names the file and what to fix.
"""
import json
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from gemlin import pet  # noqa: E402

ART = pet.ART
KEYS = {"#ff8080", "#ff0000", "#800000", "#8080ff", "#0000ff", "#000080", "#00ff00"}  # recolored by the code
FIXED = {"#0f1b27", "#fff4de", "#ffb5a0"}  # outline, cream, peach
SPRITES = sorted(p for folder in ("body", "eyes", "mouth", "hat", "reactions") for p in (ART / folder).rglob("*.png"))
FX = sorted((ART / "fx").glob("*.png")) if (ART / "fx").exists() else []
POSES = ART / "poses.json"
CYCLES = {"side_step": 6, "side_run": 4}  # frames in each cycle: all of them, or none yet


def name(path):
    return path.relative_to(ART).as_posix()


def size(path):
    width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", path.read_bytes()[16:29])
    return width, height, depth, color, interlace


def colors(path):
    return {"#%02x%02x%02x" % tuple(line[x:x + 3]) for line in pet.png_lines(path)
            for x in range(0, len(line), 4) if line[x + 3]}


def poses():
    return json.loads(POSES.read_text(encoding="utf-8")) if POSES.exists() else {}


@pytest.mark.parametrize("path", SPRITES + FX, ids=name)
def test_format(path):
    want = (24, 24) if path in FX else (64, 64)
    width, height, depth, color, interlace = size(path)
    assert (width, height) == want, f"{name(path)} is {width}x{height}; it must be {want[0]}x{want[1]}, untrimmed"
    assert (depth, color, interlace) == (8, 6, 0), f"{name(path)} must be an 8-bit RGBA PNG, not interlaced"
    alphas = {line[x] for line in pet.png_lines(path) for x in range(3, len(line), 4)}
    assert alphas <= {0, 255}, f"{name(path)} has half-transparent pixels; every pixel must be fully on or off"


@pytest.mark.parametrize("path", SPRITES, ids=name)
def test_only_the_palette(path):
    extra = colors(path) - KEYS - FIXED
    assert not extra, f"{name(path)} uses colors outside the palette: {sorted(extra)}"


@pytest.mark.parametrize("path", sorted((ART / "body").rglob("*.png")), ids=name)
def test_the_head_stays_put(path):
    """Eyes, mouth and hats are drawn over every body frame at the same spot, so rows 0-52 (the head)
    match the standing frame, unless poses.json says where the head moved to."""
    if path.stem in poses().get("head", {}):
        return
    stand = path.parent / ("side_stand.png" if path.stem.startswith("side_") else "stand.png")
    assert pet.read_png(path)[:53] == pet.read_png(stand)[:53], \
        f"{name(path)}: the head (rows 0-52) differs from {stand.name}; keep it locked, or add the offset to poses.json"


@pytest.mark.parametrize("prefix, count", CYCLES.items())
def test_cycles_are_complete(prefix, count):
    for body in (ART / "body").iterdir():
        have = sorted(p.stem for p in body.glob(f"{prefix}_*.png"))
        assert have in ([], [f"{prefix}_{i}" for i in range(1, count + 1)]), \
            f"body/{body.name}: {prefix} needs all {count} frames ({prefix}_1 to {prefix}_{count}), found {have}"


def test_poses_json():
    if not POSES.exists():
        return
    data = poses()  # plain JSON: no comments
    frames = {p.stem for p in (ART / "body").rglob("*.png")}
    for key in ("stride", "run_stride"):
        assert isinstance(data.get(key, 1), int) and data.get(key, 1) > 0, f"poses.json {key} must be a whole number of pixels"
    for frame, bob in data.get("bob", {}).items():
        assert frame in frames and isinstance(bob, int), f"poses.json bob: {frame} must be a body frame, with a whole number"
    for frame, offset in data.get("head", {}).items():
        assert frame in frames, f"poses.json head: there is no body frame called {frame}"
        assert isinstance(offset, list) and len(offset) == 2 and all(isinstance(v, int) for v in offset), \
            f"poses.json head: {frame} must be [x, y] in whole pixels"
