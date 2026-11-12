"""Vertical "rotate your phone" delivery for Instagram/TikTok.

Trick: the master is a horizontal 1920x1080 reel. For the vertical feed we show
a short vertical intro card ("turn your phone"), then the horizontal content
rotated 90 degrees so that when the viewer rotates their phone it fills the
screen at full resolution. `transpose=1` (clockwise) means the viewer rotates
LEFT (counter-clockwise) to watch upright.
"""
import os
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont
from . import ffmpeg_helpers as ff

CREAM = (235, 225, 190)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _spaced(d, text, font, y, W, sp, fill, sw, sfill):
    ws = [d.textlength(c, font=font) for c in text]
    x = (W - (sum(ws) + sp * (len(text) - 1))) / 2
    for c, w in zip(text, ws):
        d.text((x, y), c, font=font, fill=fill, stroke_width=sw, stroke_fill=sfill)
        x += w + sp


def _make_intro(cfg, outp, dur=2.8, W=1080, H=1920):
    im = Image.new("RGB", (W, H), (8, 8, 10))
    d = ImageDraw.Draw(im)
    cx, cy = W // 2, H // 2 - 140
    pw, ph = 150, 264
    d.rounded_rectangle([cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2], radius=26, outline=CREAM, width=8)
    R = 250
    d.arc([cx - R, cy - R, cx + R, cy + R], start=190, end=335, fill=CREAM, width=11)
    a = math.radians(190)
    ex, ey = cx + R * math.cos(a), cy + R * math.sin(a)
    d.polygon([(ex - 22, ey + 2), (ex + 10, ey - 16), (ex + 6, ey + 24)], fill=CREAM)
    _spaced(d, "ROTATE YOUR PHONE", _font(cfg.font_bold, 82), cy + ph // 2 + 96, W, 6, (255, 255, 255, 255), 4, (0, 0, 0, 220))
    _spaced(d, "WATCH IN LANDSCAPE", _font(cfg.font_regular, 42), cy + ph // 2 + 210, W, 6, CREAM, 2, (0, 0, 0, 180))
    png = os.path.join(cfg.tmp_dir, "_vintro.png")
    im.save(png)
    ff.run(["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", png,
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
            "-r", str(cfg.FPS), "-vf", f"scale={W}:{H},fade=t=in:d=0.4,format=yuv420p"]
           + ff.SEG_VCODEC + ff.SEG_ACODEC + [outp], timeout=120)


def build_vertical(cfg, master_path, tag="vertical"):
    """Produce a 1080x1920 vertical cut from a horizontal master."""
    W, H = 1080, 1920
    intro = os.path.join(cfg.tmp_dir, f"_vintro_{tag}.mp4")
    _make_intro(cfg, intro, W=W, H=H)
    rot = os.path.join(cfg.tmp_dir, f"_rot_{tag}.mp4")
    ff.run(["ffmpeg", "-y", "-i", master_path,
            "-vf", f"transpose=1,scale={W}:{H},setsar=1,format=yuv420p", "-r", str(cfg.FPS)]
           + ff.SEG_VCODEC + ff.SEG_ACODEC + [rot], timeout=900)
    base = os.path.splitext(os.path.basename(master_path))[0]
    out = os.path.join(cfg.output_dir, f"{base}_VERTICAL.mp4")
    r = subprocess.run(["ffmpeg", "-y", "-i", intro, "-i", rot, "-filter_complex",
                        "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]"]
                       + ff.FINAL_VCODEC + ff.FINAL_ACODEC + ["-movflags", "+faststart", out],
                       stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, timeout=900)
    if r.returncode == 0:
        print(f"OK  {os.path.basename(out)}  {ff.probe_duration(out):.0f}s  {W}x{H}")
        return out
    print("FAILED vertical:", r.stderr.decode()[-400:])
    return None
