# Art request 3: motion and personality

For the art agent. Draw the sprites below and put them straight into this repo's `gemlin/art/` folder, then run the checks at the end. The code is written separately and picks up each file as soon as it exists; anything missing falls back to the frame listed, so you can deliver in batches.

**Why:** Gemlin moves stiffly. The side walk alternates only two poses (`side_walk_1`, `side_walk_2`), so he shuffles and his feet slide. Standing still, he's a statue, and he has one expression. These frames give him a real walk, breathing, glances, gestures and moods.

**Builds on:** creator pack v8 (everything in `gemlin/art/` today) and reactions v1 (`gemlin/art/reactions/`). Match their style, proportions and palette exactly. Open the existing PNGs before drawing.

## Rules (same as v8)

- 64 × 64 px, 8-bit RGBA PNG, untrimmed. Effects in `fx/` are 24 × 24.
- Binary alpha: every pixel fully opaque or fully transparent. No soft edges, glows or shadows.
- Only these 10 colors, the same as v8:
  - recolored by the code: body `#FF8080` `#FF0000` `#800000`, hat accent `#8080FF` `#0000FF` `#000080`, eyes `#00FF00`
  - fixed: outline and mouth `#0F1B27`, cream `#FFF4DE`, cheek and tongue `#FFB5A0`
  - Effects in `fx/` may use other colors.
- **Layered frames stay layered.** New body frames have no eyes or mouth. The game draws body → eyes → mouth → hat, so every new pose has to work with all 8 hats.
- **The head stays put.** In body frames, rows 0–52 (the head) must match `stand.png` (front) or `side_stand.png` (side) pixel for pixel. If a pose needs the head somewhere else (sitting, peeking), draw it there and record the offset in `poses.json`; the code moves the eyes, mouth and hat by the same amount.
- Side views face right; the code mirrors them to walk left.
- Feet touch row 63 whenever they're on the ground.
- New eye and mouth frames stay inside the v8 face area, so every hat still fits.

## The walk cycle (most important)

Six frames, one full cycle of two steps, facing right, in `gemlin/art/body/gem/`:

| Frame | Pose | Suggested bob |
|---|---|---|
| `side_step_1.png` | contact: right foot forward, heel down | 0 |
| `side_step_2.png` | down: weight lands, body lowest | +1 |
| `side_step_3.png` | passing: back leg swings under, body highest | −1 |
| `side_step_4.png` | contact: left foot forward | 0 |
| `side_step_5.png` | down | +1 |
| `side_step_6.png` | passing, flows back into frame 1 | −1 |

The code plays them at about 10 frames a second and moves Gemlin forward at the same speed his feet move. Keep the head locked; the code bobs the whole sprite by the amounts in `poses.json` (+ is down, in art pixels). Swing the arms opposite to the legs if they show. Measure the **stride**: how many pixels the front foot travels across one full cycle. It goes in `poses.json`.

## What to draw

**First** = what makes him feel alive. **Later** = more personality.

### Body: `gemlin/art/body/gem/` (layered)

| File | Pose | Used when | Priority | Falls back to |
|---|---|---|---|---|
| `side_step_1.png` … `side_step_6.png` | the walk cycle above | walking (most of his day) | first | `side_walk_1`, `side_walk_2` |
| `idle_1.png`, `idle_2.png` | breathing: belly and shoulders rise 1 px, then a bit more; loops stand → idle_1 → idle_2 → idle_1 | standing still | first | `stand` |
| `wave_1.png`, `wave_2.png` | one arm up, waving, two positions | saying hi, when you come back, when clicked | first | `stand` |
| `sit.png` | sitting on the floor, legs forward; head may drop (record it) | resting, waiting for you | first | `stand` |
| `side_run_1.png` … `side_run_4.png` | quick run, leaning forward; head offsets per frame if it leans | dashing now and then | later | `side_step` |
| `side_idle_1.png` | breathing, side view | pausing mid-walk | later | `side_stand` |
| `stretch.png` | both arms up, stretching | yawning, waking up | later | `stand` |
| `side_peek.png` | leaning over the screen edge, looking down; head offset | reaching the edge of the screen | later | `side_stand` |

### Eyes: `gemlin/art/eyes/round/`

| File | Look | Used when | Priority | Falls back to |
|---|---|---|---|---|
| `look_left.png`, `look_right.png` | pupils glancing to one side | following the mouse pointer, looking around | first | `open` |
| `happy.png` | happy squint, ^ ^ | petted, good news, waving | first | `blink` |
| `sleepy.png` | half-closed lids | late at night, bored, before a nap | first | `open` |
| `look_up.png` | looking up and to the side | thinking | later | `open` |
| `wide.png` | wide open, surprised | something popped up | later | `open` |
| `side_happy.png`, `side_sleepy.png` | the same, side view | while walking | later | `side_open` |

### Mouth: `gemlin/art/mouth/smile/`

| File | Look | Used when | Priority | Falls back to |
|---|---|---|---|---|
| `talk_2.png` | half open | talking (closed → talk_2 → talk_1) | first | `closed` |
| `grin.png` | big open smile | happy, waving, celebrating | first | `closed` |
| `oh.png` | small round "oh" | surprised, curious | later | `talk_1` |
| `yawn.png` | wide yawn | sleepy, with `stretch.png` | later | `talk_1` |
| `side_talk_2.png`, `side_grin.png` | the same, side view | talking or happy while walking | later | `side_closed` |

### Effects: `gemlin/art/fx/` (new folder, 24 × 24, any colors, floats above the head)

| File | Look | Used when | Priority |
|---|---|---|---|
| `zzz_1.png` … `zzz_3.png` | floating Z's, growing | napping | first |
| `heart_1.png`, `heart_2.png` | a heart popping up | petted, happy | first |
| `alert_1.png`, `alert_2.png` | bouncing "!" | needs your answer, noticed something | first |
| `question_1.png`, `question_2.png` | bouncing "?" | curious | later |
| `sweat_1.png`, `sweat_2.png` | sweat drop | something went wrong | later |
| `note_1.png`, `note_2.png` | music notes | humming while walking | later |
| `sparkle_1.png`, `sparkle_2.png` | sparkles | celebrating, new look | later |
| `dust_1.png`, `dust_2.png` | small dust puff (drawn at the feet) | landing, starting a run | later |

### Reactions: `gemlin/art/reactions/` (whole character, no hat, like reactions v1)

| File | Look | Used when | Priority | Falls back to |
|---|---|---|---|---|
| `side_falling.png`, `side_landed.png`, `side_recovering.png` | the v1 drop reactions, side view (right-facing) | dropped while walking | later | front versions |
| `dizzy_1.png`, `dizzy_2.png` | swirly eyes, wobbling | dragged around a lot | later | `recovering` |

First batch: 24 files. Later batch: 30 files.

## `gemlin/art/poses.json`

Plain JSON (no comments). Offsets are art pixels, `[x, y]`, y down. Leave out anything that's zero. Example (use your real numbers):

```json
{
  "stride": 28,
  "run_stride": 36,
  "bob": {"side_step_1": 0, "side_step_2": 1, "side_step_3": -1, "side_step_4": 0, "side_step_5": 1, "side_step_6": -1},
  "head": {"sit": [0, 6], "side_peek": [4, 3]}
}
```

- `stride` / `run_stride`: pixels the front foot travels in one full walk / run cycle.
- `bob`: how far to drop (+) or lift (−) the whole sprite on each walk or run frame.
- `head`: where the head moved to in frames that don't keep it locked. Every frame whose head differs from the standing frame must be listed here.

## Check your work

From the repo root:

```
python -m gemlin.pet --manifest     # updates gemlin/art/manifest.json (the website reads it)
python -m pytest tests/test_art.py tests/test_pet.py
```

`tests/test_art.py` checks size, format, binary alpha, the palette, the locked head, complete cycles and `poses.json`. Each failure names the file and what to fix.

Also save a preview GIF of the walk cycle with the crown and the wizard hat on, and a contact sheet of the new frames, to `docs/art-requests/03-motion-preview/`, so the work can be reviewed without running the app. Keep your source files and prompts there too.

Don't edit anything outside `gemlin/art/` and `docs/art-requests/03-motion-preview/`.
