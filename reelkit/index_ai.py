"""AI content indexing with Gemini: describe what is on screen, window by
window, so you (and your AI assistant) can find the good moments without
re-watching hours of footage.

Lessons baked in:
  * Use a decent proxy: 720p / 4fps / MEDIA_RESOLUTION_HIGH. Low-res/low-fps
    proxies make brief events (a dog, a skid) vanish.
  * BRIGHTEN dark windows before sending; Gemini can't see near-black.
  * Demand a per-line list with timestamps and a USE/DISCARD verdict, not a
    vague summary.
  * Gemini will still INVENT foreign-language signage (e.g. plausible Chinese
    place names) on dark 360 footage. Run the guardrail afterwards.

google-genai is optional; imported lazily so the rest of the toolkit works
without it.
"""
import os
import tempfile
import subprocess
from PIL import Image, ImageStat

PROMPT = (
    "This is a {window}s window of a motorcycle trip ({loc}). If it looks "
    "brightened it was dark. Do NOT summarise vaguely. List, with mm:ss-mm:ss "
    "timestamps, everything useful for editing a reel: PEOPLE (police/customs, "
    "onlookers, other riders), ANIMALS (dogs: say if they chase), readable "
    "SIGNS (place names, borders), strong LANDSCAPE/LANDMARKS (mountains, gorge, "
    "city skyline, border post), sudden EVENTS (skid, hard braking, something "
    "crossing), and HERO-SHOT candidates (a beautiful, stable shot - give the "
    "second). One line each: mm:ss-mm:ss | TYPE | concrete description | USE/DISCARD"
)


def _dur(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", v], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _is_dark(cfg, v, at):
    fd, p = tempfile.mkstemp(suffix=".jpg", dir=cfg.tmp_dir)
    os.close(fd)
    try:
        r = subprocess.run(["ffmpeg", "-y", "-ss", str(at), "-i", v, "-frames:v", "1",
                            "-vf", "scale=64:36", p], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        if r.returncode != 0:
            return False
        return ImageStat.Stat(Image.open(p).convert("L")).mean[0] < 45
    except Exception:
        return False
    finally:
        try:
            os.remove(p)
        except OSError:
            pass


def _proxy(cfg, v, st, ln, night):
    """Render a brightened low-res proxy. Returns its path, or None if ffmpeg
    failed (caller must not upload a failed/empty file)."""
    fd, out = tempfile.mkstemp(suffix=".mp4", dir=cfg.tmp_dir)
    os.close(fd)
    g = "eq=brightness=0.20:gamma=1.8:contrast=1.05," if night else ""
    vf = f"{g}scale={cfg.index_px}:-2,fps={cfg.index_fps}"
    r = subprocess.run(["ffmpeg", "-y", "-ss", str(st), "-i", v, "-t", str(ln), "-vf", vf,
                        "-c:v", "libx264", "-crf", "27", "-preset", "veryfast", "-an", out],
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) < 1000:
        try:
            os.remove(out)
        except OSError:
            pass
        return None
    return out


def index_clip(cfg, clip_path, loc, out_txt):
    """Index one clip into a text file. Skips if out_txt exists (resumable)."""
    if os.path.exists(out_txt):
        return "skip"
    from google import genai
    from google.genai import types
    key = cfg.gemini_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    client = genai.Client(api_key=key)
    D = _dur(clip_path)
    res = [f"# {os.path.basename(clip_path)}  {loc}  dur={int(D)}s"]

    def mmss(s):
        return f"{int(s)//60:02d}:{int(s)%60:02d}"

    st = 0
    while st < D:
        ln = min(cfg.index_window_s, D - st)
        night = _is_dark(cfg, clip_path, st + ln / 2)
        px = _proxy(cfg, clip_path, st, ln, night)
        if not px:
            res.append(f"\n## window {mmss(st)} ERROR proxy render failed")
            st += cfg.index_window_s
            continue
        try:
            b = open(px, "rb").read()
            r = client.models.generate_content(
                model=cfg.gemini_model,
                contents=[{"inline_data": {"mime_type": "video/mp4", "data": b}},
                          PROMPT.format(loc=loc, window=int(ln))],
                config=types.GenerateContentConfig(media_resolution="MEDIA_RESOLUTION_HIGH"))
            res.append(f"\n## window {mmss(st)} (+{int(ln)}s){' [brightened]' if night else ''}\n" + r.text.strip())
        except Exception as e:
            res.append(f"\n## window {mmss(st)} ERROR {e}")
        finally:
            try:
                os.remove(px)
            except OSError:
                pass
        st += cfg.index_window_s
    os.makedirs(os.path.dirname(out_txt) or ".", exist_ok=True)
    open(out_txt, "w", encoding="utf-8").write("\n".join(res))
    return "ok"
