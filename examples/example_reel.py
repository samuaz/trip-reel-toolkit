#!/usr/bin/env python3
"""Example reel script. Copy it, point the clip names at your own footage, and
build with:

    python3 scripts/build_reel.py examples/example_reel.py --vertical

A reel is just three names the builder looks for: SHOTS, OUTPUT, MUSIC.
Every shot is a dict — see reelkit/builder.py for the full shot schema.

Structure that works: HOOK -> BODY -> CLIMAX -> CLOSE. Prefer long shots
(8-14s), crossfades (automatic), and let real voice carry the story. Keep a
strict chronological order.
"""

# cam/src below must match camera names in your config.yaml and real clip
# basenames (filename without extension). These are placeholders.
POV = "pov"
SPH = "sphere"

SHOTS = [
    # --- HOOK: open on your strongest/most intriguing moment -----------------
    {"kind": "clip", "cam": POV, "src": "CLIP_HOOK", "ss": 150, "dur": 4.0,
     "grade": "dlog", "sub": "Lost, no GPS: asking a border guard the way"},

    # --- TITLE ---------------------------------------------------------------
    {"kind": "title", "title": "MY TRIP", "subtitle": "PART 1 · THE START", "dur": 2.6},

    # --- BODY: establish with 360, carry voice with POV ----------------------
    {"kind": "clip", "cam": SPH, "src": "CLIP_360_A", "ss": 20, "dur": 6.5,
     "angle": "front", "sub": "At dusk I ride into town"},
    {"kind": "clip", "cam": SPH, "src": "CLIP_360_A", "ss": 300, "dur": 6.5,
     "angle": "hero"},
    # a 360 shot that BORROWS the POV mic so a line of dialogue stays continuous:
    {"kind": "clip", "cam": SPH, "src": "CLIP_360_A", "ss": 640, "dur": 6.0,
     "angle": "hero", "audio_from": (POV, "CLIP_POV_DIALOG", 405),
     "sub": [(0.2, 3.3, "- Where are you headed?"), (3.5, 6.0, "- East, as far as it goes")]},

    # a still photo with a gentle push-in:
    {"kind": "photo", "img": "/absolute/path/to/photo.jpg", "dur": 3.2,
     "sub": "A stranger who became a friend"},

    # a POV shot with a blurred number plate (x, y, w, h in canvas pixels):
    {"kind": "clip", "cam": POV, "src": "CLIP_POV_ARRIVE", "ss": 1052, "dur": 8.0,
     "grade": "dlog", "sub": "\"Here's the garage\" - he puts me up for the night",
     "blur": [(160, 430, 420, 240)]},

    # --- CLOSE / cliffhanger card -------------------------------------------
    {"kind": "card", "main": "TO BE CONTINUED", "sub": "PART 2", "dur": 3.4},
]

OUTPUT = "EXAMPLE_REEL.mp4"
MUSIC = "epic_01.mp3"   # a file in your music_dir, or None
