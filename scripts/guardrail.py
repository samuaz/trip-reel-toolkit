#!/usr/bin/env python3
"""Run the deterministic anti-hallucination guardrail over a catalog directory.

Dry-run (default) just reports; --apply rewrites the files.

Usage:
    python3 scripts/guardrail.py --dir ~/trip-reels/output/catalog
    python3 scripts/guardrail.py --dir ~/trip-reels/output/catalog --apply
"""
import argparse
import os
import _bootstrap  # noqa: F401
from reelkit import config
from reelkit.guardrail import process_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = config.load(args.config)
    process_dir(cfg, os.path.expanduser(args.dir), apply=args.apply)


if __name__ == "__main__":
    main()
