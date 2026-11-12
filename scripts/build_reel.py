#!/usr/bin/env python3
"""Build a reel from a reel-script file.

A reel script is a .py that defines:
    SHOTS   = [ {...}, {...} ]      # list of shot dicts (see reelkit/builder.py)
    OUTPUT  = "MY_REEL.mp4"         # output filename
    MUSIC   = "epic_01.mp3"         # optional music bed name (in music_dir)

Usage:
    python3 scripts/build_reel.py path/to/my_reel.py [--vertical] [--config config.yaml]
"""
import argparse
import importlib.util
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.builder import Builder
from reelkit.vertical import build_vertical


def load_reel(path):
    spec = importlib.util.spec_from_file_location("reel_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reel_script", help="path to a .py reel script (SHOTS/OUTPUT/MUSIC)")
    ap.add_argument("--vertical", action="store_true", help="also produce a vertical cut")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    cfg = config.load(args.config)
    reel = load_reel(args.reel_script)
    shots = getattr(reel, "SHOTS")
    out = getattr(reel, "OUTPUT", "REEL.mp4")
    music = getattr(reel, "MUSIC", None)

    b = Builder(cfg)
    master = b.assemble(shots, out, music=music)
    if master and args.vertical:
        build_vertical(cfg, master)


if __name__ == "__main__":
    main()
