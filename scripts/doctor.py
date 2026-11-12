#!/usr/bin/env python3
"""Preflight check: tell you (and your AI assistant) exactly what is installed
and what is missing, with copy-paste commands to fix each gap.

    python3 scripts/doctor.py

Exit code 0 means the CORE (reels can be built) is ready. Non-zero means a core
dependency is missing. Optional features (whisper / Gemini / demucs) are
reported but never fail the check.
"""
import sys
import os
import shutil
import platform
import subprocess

OSX = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
WIN = os.name == "nt"


def pkg_cmd(brew, apt):
    if OSX:
        return brew
    if LINUX:
        return apt
    return f"(install manually) {brew}"


OK, MISS, OPT = "  OK  ", " MISS ", " opt  "
core_ok = True
lines = []


def check(label, present, fix=None, optional=False):
    global core_ok
    tag = OK if present else (OPT if optional else MISS)
    lines.append(f"[{tag}] {label}")
    if not present:
        if fix:
            lines.append(f"         fix: {fix}")
        if not optional:
            core_ok = False


def importable(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def main():
    print("=" * 64)
    print(f" trip-reel-toolkit doctor   ({platform.platform()})")
    print("=" * 64)

    # --- core ---------------------------------------------------------------
    check(f"Python {sys.version.split()[0]} (>=3.9)", sys.version_info >= (3, 9),
          "install Python 3.9+")
    check("ffmpeg", bool(shutil.which("ffmpeg")),
          pkg_cmd("brew install ffmpeg", "sudo apt install ffmpeg"))
    check("ffprobe", bool(shutil.which("ffprobe")),
          pkg_cmd("brew install ffmpeg", "sudo apt install ffmpeg"))
    check("Python: PyYAML", importable("yaml"), "pip3 install -r requirements.txt")
    check("Python: Pillow", importable("PIL"), "pip3 install -r requirements.txt")

    # drawtext note (informational — the toolkit does NOT need it)
    if shutil.which("ffmpeg"):
        try:
            out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                                 capture_output=True, text=True, timeout=30).stdout
            has = " drawtext " in out
            lines.append(f"[ info ] ffmpeg drawtext filter: "
                         f"{'present' if has else 'absent (fine — captions use PIL overlays)'}")
        except Exception:
            pass

    # --- optional: transcription -------------------------------------------
    wc = shutil.which("whisper-cli") or shutil.which("whisper-cpp")
    check("whisper.cpp (local transcription)", bool(wc),
          pkg_cmd("brew install whisper-cpp", "build from https://github.com/ggml-org/whisper.cpp")
          + "  then download a model (e.g. ggml-large-v3-turbo-q5_0.bin)", optional=True)

    # --- optional: AI (Gemini) ---------------------------------------------
    check("Python: google-genai (AI indexing/music)", importable("google.genai"),
          "pip3 install -r requirements-optional.txt", optional=True)
    check("GEMINI_API_KEY in environment",
          bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
          "export GEMINI_API_KEY=your_key", optional=True)

    # --- optional: audio cleanup -------------------------------------------
    check("Python: demucs (voice removal)", importable("demucs"),
          "pip3 install -r requirements-optional.txt  (pulls PyTorch, ~1-2 GB)", optional=True)

    # --- config -------------------------------------------------------------
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_exists = os.path.exists(os.path.join(here, "config.yaml"))
    check("config.yaml", cfg_exists, "python3 wizard.py", optional=True)

    print("\n".join(lines))
    print("-" * 64)
    if core_ok:
        print("CORE READY — you can build reels.")
        if not cfg_exists:
            print("Next: python3 wizard.py")
    else:
        print("CORE INCOMPLETE — install the MISS items above, then re-run the doctor.")
    print("Optional 'opt' items unlock transcription / AI indexing / audio cleanup.")
    sys.exit(0 if core_ok else 1)


if __name__ == "__main__":
    main()
