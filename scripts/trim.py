#!/usr/bin/env python3
"""Lossless trim: keep only chosen spans of a clip.

Spans are "start-end" in seconds, comma-separated:
    python3 scripts/trim.py --cam pov --clip CLIP_0001 --spans 12-40,120-156
    python3 scripts/trim.py --path /abs/clip.mp4 --spans 0-30 --out out.mp4
"""
import argparse
import os
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.trim import trim_keep, merge_spans


def parse_spans(s):
    out = []
    for chunk in s.split(","):
        a, b = chunk.split("-")
        out.append((float(a), float(b)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam")
    ap.add_argument("--clip")
    ap.add_argument("--path")
    ap.add_argument("--spans", required=True)
    ap.add_argument("--pad", type=int, default=3)
    ap.add_argument("--out")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = config.load(args.config)
    src = args.path or cfg.resolve_clip(args.cam, args.clip)
    if not src:
        raise SystemExit("clip not found")
    spans = merge_spans(parse_spans(args.spans), pad=args.pad)
    base = os.path.splitext(os.path.basename(src))[0]
    out = args.out or os.path.join(cfg.output_dir, "selects", base + "_trimmed.mp4")
    print(trim_keep(src, spans, out))


if __name__ == "__main__":
    main()
