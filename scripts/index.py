#!/usr/bin/env python3
"""AI-index clips with Gemini into per-clip catalog text files.

Needs GEMINI_API_KEY in the environment.

A list file has one "cam<TAB>clip<TAB>location" per line:
    pov<TAB>CLIP_0001<TAB>Mountain pass at dusk

Usage:
    python3 scripts/index.py --list clips.txt
    python3 scripts/index.py --cam pov --clip CLIP_0001 --loc "Border post"
Then always run the guardrail (scripts/guardrail.py) over the output dir.
"""
import argparse
import os
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.index_ai import index_clip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list")
    ap.add_argument("--cam")
    ap.add_argument("--clip")
    ap.add_argument("--loc", default="")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = config.load(args.config)
    outdir = os.path.join(cfg.output_dir, "catalog")

    jobs = []
    if args.list:
        for ln in open(args.list, encoding="utf-8"):
            ln = ln.rstrip("\n")
            if not ln or ln.startswith("#"):
                continue
            parts = ln.split("\t")
            cam, clip = parts[0], parts[1]
            loc = parts[2] if len(parts) > 2 else ""
            jobs.append((cam, clip, loc))
    elif args.clip:
        jobs.append((args.cam, args.clip, args.loc))
    else:
        raise SystemExit("give --clip or --list")

    for cam, clip, loc in jobs:
        src = cfg.resolve_clip(cam, clip)
        if not src:
            print("MISSING", cam, clip)
            continue
        out = os.path.join(outdir, clip + ".txt")
        try:
            print(index_clip(cfg, src, loc, out), clip)
        except Exception as e:
            print("ERR", clip, e)
    print("Remember: python3 scripts/guardrail.py --dir", outdir, "--apply")


if __name__ == "__main__":
    main()
