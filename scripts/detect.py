#!/usr/bin/env python3
"""Multi-signal event detection for a clip (audio peaks + whisper hallucination).

Usage:
    python3 scripts/detect.py --cam pov --clip CLIP_BASENAME [--srt path.srt]
    python3 scripts/detect.py --path /abs/clip.mp4 --srt /abs/clip.srt
"""
import argparse
import os
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.detect import analyze


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam")
    ap.add_argument("--clip")
    ap.add_argument("--path")
    ap.add_argument("--srt")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = config.load(args.config)
    src = args.path or cfg.resolve_clip(args.cam, args.clip)
    if not src:
        raise SystemExit("clip not found")
    srt = args.srt
    if not srt and args.clip:
        cand = os.path.join(cfg.output_dir, "srt", args.clip + ".srt")
        srt = cand if os.path.exists(cand) else None
    report, _ = analyze(src, srt)
    print(report)


if __name__ == "__main__":
    main()
