#!/usr/bin/env python3
"""Transcribe clips to .srt with whisper.cpp (local).

Single clip:
    python3 scripts/transcribe.py --cam pov --clip CLIP_BASENAME
A resumable sweep over a queue file (one "cam<TAB>clip" per line):
    python3 scripts/transcribe.py --queue queue.txt
SRTs are written to <output_dir>/srt/ and skipped if already present.
"""
import argparse
import os
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.transcribe import transcribe_clip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam")
    ap.add_argument("--clip")
    ap.add_argument("--queue")
    ap.add_argument("--ss", type=float, default=0)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = config.load(args.config)
    srtdir = os.path.join(cfg.output_dir, "srt")

    jobs = []
    if args.queue:
        for ln in open(args.queue):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            cam, clip = (ln.split("\t") + [None])[:2] if "\t" in ln else (args.cam, ln)
            jobs.append((cam, clip))
    elif args.clip:
        jobs.append((args.cam, args.clip))
    else:
        raise SystemExit("give --clip or --queue")

    for cam, clip in jobs:
        src = cfg.resolve_clip(cam, clip)
        if not src:
            print("MISSING", cam, clip)
            continue
        out = os.path.join(srtdir, clip + ".srt")
        r = transcribe_clip(cfg, src, out, ss=args.ss, dur=args.dur)
        print("OK" if r else "FAIL", clip)


if __name__ == "__main__":
    main()
