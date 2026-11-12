#!/usr/bin/env python3
"""Generate instrumental music beds with Lyria. Needs GEMINI_API_KEY.

Edit JOBS below to describe the scores you want, then run:
    python3 scripts/gen_music.py
Files land in your configured music_dir and are skipped if they already exist.
"""
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.music import generate

# name -> prompt. Describe a cinematic, VOCAL-FREE film score + the emotional arc.
JOBS = {
    "tense_01": ("Cinematic tense driving instrumental for a dangerous night ride on a gravel "
                 "road: relentless low pulse, gritty percussion, rising dread and adrenaline, "
                 "dark and cold. No vocals. Film score."),
    "epic_01": ("Cinematic epic emotional instrumental: soaring strings, warm and hopeful, grand "
                "mountains at dawn, a sense of reward and awe after hardship. No vocals. "
                "Documentary film score."),
    "triumph_01": ("Cinematic triumphant climactic instrumental: powerful swelling orchestra, "
                   "crossing into the unknown, hopeful and resolute, a hard journey paying off. "
                   "No vocals. Epic film score."),
}

if __name__ == "__main__":
    cfg = config.load()
    generate(cfg, JOBS)
    print("MUSIC_DONE")
