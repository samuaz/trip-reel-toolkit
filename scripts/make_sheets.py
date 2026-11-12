#!/usr/bin/env python3
"""Contact sheet for a clip (grid of timestamped thumbnails).

Usage:
    python3 scripts/make_sheets.py --cam pov --clip CLIP_BASENAME
    python3 scripts/make_sheets.py --path /abs/path/to/clip.mp4 --sample 30
"""
import argparse
import os
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.sheets import sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam")
    ap.add_argument("--clip")
    ap.add_argument("--path")
    ap.add_argument("--sample", type=int, default=45, help="seconds between thumbnails")
    ap.add_argument("--out")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = config.load(args.config)

    src = args.path or cfg.resolve_clip(args.cam, args.clip)
    if not src:
        raise SystemExit("clip not found")
    out = args.out or os.path.join(cfg.output_dir, "sheets",
                                   os.path.splitext(os.path.basename(src))[0] + ".png")
    print(sheet(cfg, src, out, sample=args.sample))


if __name__ == "__main__":
    main()
