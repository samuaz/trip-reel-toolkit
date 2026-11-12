#!/usr/bin/env python3
"""Interactive configurator for trip-reel-toolkit.

Run it once on a new machine:  python3 wizard.py

It starts from config.example.yaml (so you keep the tuned color grades, 360
angles and audio filters) and asks only for what is specific to you: project
name, folders, your cameras, fonts, whisper, API keys and the optional
hallucination guardrail. It writes config.yaml.

Nothing here is destructive: it refuses to overwrite an existing config.yaml
unless you confirm, and it only probes for tools (ffmpeg / whisper) — it never
installs anything.
"""
import os
import shutil
import subprocess
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(HERE, "config.example.yaml")
TARGET = os.path.join(HERE, "config.yaml")


# -- tiny prompt helpers ------------------------------------------------------
def ask(prompt, default=""):
    d = f" [{default}]" if default != "" else ""
    val = input(f"{prompt}{d}: ").strip()
    return val or default


def ask_bool(prompt, default=True):
    d = "Y/n" if default else "y/N"
    val = input(f"{prompt} [{d}]: ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


def which(name):
    return shutil.which(name)


def probe_ffmpeg():
    exe = which("ffmpeg")
    if not exe:
        print("  !! ffmpeg not found on PATH. Install it before building reels.")
        return
    try:
        out = subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30).stdout
        has_drawtext = " drawtext " in out
        print(f"  ffmpeg: {exe}")
        print(f"  drawtext filter: {'present' if has_drawtext else 'ABSENT (fine - we use PIL overlays)'}")
    except Exception:
        print(f"  ffmpeg: {exe}")


# -- sections -----------------------------------------------------------------
def section_project(cfg):
    print("\n== Project ==")
    cfg["project"]["name"] = ask("Project / trip name", cfg["project"]["name"])
    cfg["project"]["output_dir"] = ask("Output folder (finished reels)", cfg["project"]["output_dir"])
    cfg["project"]["tmp_dir"] = ask("Temp/render cache folder", cfg["project"]["tmp_dir"])


def section_cameras(cfg):
    print("\n== Cameras ==")
    print("Define each camera you shoot with. Types:")
    print("  pov        flat 16:9 footage with a mic (DJI/GoPro helmet cam)")
    print("  sphere360  dual-fisheye 360 (Insta360 / Osmo 360), reframed with v360")
    print("  photo      stills (no path needed; you pass image paths in shots)")
    if not ask_bool("Reconfigure cameras now?", True):
        return
    cams = {}
    n = 1
    while True:
        print(f"\n  -- camera #{n} --")
        name = ask("  short name you'll use in shot lists (blank to finish)")
        if not name:
            break
        ctype = ask("  type (pov/sphere360/photo)", "pov")
        cam = {"type": ctype}
        if ctype != "photo":
            cam["path"] = ask("  footage folder")
            cam["has_mic"] = ask_bool("  does it carry usable voice (a mic)?", ctype == "pov")
            exts = ask("  file extensions (comma)", "MP4,mp4" if ctype == "pov" else "insv,mp4")
            cam["extensions"] = [e.strip() for e in exts.split(",") if e.strip()]
        cams[name] = cam
        n += 1
    if cams:
        cfg["cameras"] = cams


def section_fonts(cfg):
    print("\n== Fonts ==")
    print("Leave blank to auto-detect a system font (recommended).")
    cfg["fonts"]["bold"] = ask("Bold font path", cfg["fonts"].get("bold", ""))
    cfg["fonts"]["regular"] = ask("Regular font path", cfg["fonts"].get("regular", ""))


def section_tools(cfg):
    print("\n== Tools ==")
    probe_ffmpeg()
    wc = which("whisper-cli") or which("whisper-cpp") or ""
    print(f"  whisper.cpp binary: {wc or 'not found on PATH'}")
    if ask_bool("Configure whisper transcription (local, free)?", bool(wc)):
        cfg["tools"]["whisper_cli"] = ask("  whisper-cli path", wc)
        cfg["tools"]["whisper_model"] = ask("  whisper model path (ggml-*.bin)",
                                            cfg["tools"].get("whisper_model", ""))
        cfg["tools"]["whisper_lang"] = ask("  spoken language code", cfg["tools"].get("whisper_lang", "en"))
    else:
        cfg["tools"]["whisper_cli"] = ""
        cfg["tools"]["whisper_model"] = ""
    cfg["tools"]["ffmpeg_workers"] = int(ask("  parallel ffmpeg workers (1 if footage is on a flaky external disk)",
                                             str(cfg["tools"].get("ffmpeg_workers", 1))))


def section_music(cfg):
    print("\n== Music ==")
    cfg["audio"]["music_dir"] = ask("Music folder", cfg["audio"].get("music_dir", "~/trip-reels/music"))
    cfg["audio"]["default_music"] = ask("Default music file name (optional)",
                                        cfg["audio"].get("default_music", ""))


def section_ai(cfg):
    print("\n== AI services (optional) ==")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        print("  GEMINI_API_KEY detected in environment — AI indexing & music enabled.")
    else:
        print("  No GEMINI_API_KEY in environment. AI indexing and music generation will be")
        print("  disabled until you export GEMINI_API_KEY=... (the toolkit never stores keys).")


def section_guardrail(cfg):
    print("\n== Hallucination guardrail (optional) ==")
    print("Neutralises AI-invented signage that cannot exist before a date")
    print("(classic case: foreign-language text appearing before you reached that country).")
    if ask_bool("Enable the guardrail?", False):
        print("  Example token regex for CJK text: [\\u3400-\\u9fff\\uf900-\\ufaff]")
        cfg["guardrail"]["token_regex"] = ask("  token regex (blank = CJK example)",
                                              cfg["guardrail"].get("token_regex", "")) or "[\\u3400-\\u9fff\\uf900-\\ufaff]"
        cfg["guardrail"]["allowed_from_date"] = ask("  allowed from date (YYYYMMDD)",
                                                   cfg["guardrail"].get("allowed_from_date", ""))
        cfg["guardrail"]["filename_date_regex"] = ask("  filename date regex",
                                                     cfg["guardrail"].get("filename_date_regex", r"(20\d{6})"))
    else:
        cfg["guardrail"]["token_regex"] = ""


def main():
    if not os.path.exists(EXAMPLE):
        raise SystemExit("config.example.yaml not found next to wizard.py")
    if os.path.exists(TARGET):
        if not ask_bool(f"config.yaml already exists. Overwrite?", False):
            print("Keeping existing config.yaml. Nothing changed.")
            return
    with open(EXAMPLE, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    print("=" * 64)
    print(" trip-reel-toolkit setup")
    print(" Press Enter to accept the [default] shown in brackets.")
    print("=" * 64)
    section_project(cfg)
    section_cameras(cfg)
    section_fonts(cfg)
    section_tools(cfg)
    section_music(cfg)
    section_ai(cfg)
    section_guardrail(cfg)

    with open(TARGET, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)
    print("\nWrote", TARGET)
    print("Next: python3 scripts/make_sheets.py --cam <name> --clip <CLIP> to test it,")
    print("then read CLAUDE.md and build your first reel from examples/example_reel.py.")


if __name__ == "__main__":
    main()
