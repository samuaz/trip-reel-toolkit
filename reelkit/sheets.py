"""Contact sheets: a grid of timestamped thumbnails so you can eyeball a clip
(or only its unreviewed spans) fast. Always review by LOOKING at frames; never
pick shots from filenames or text descriptions alone.
"""
import os
import glob
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont
from . import ffmpeg_helpers as ff


def _mmss(s):
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def sheet(cfg, clip_path, out_png, sample=45, spans=None, thumb_w=360, cols=6):
    """Write a contact sheet PNG. `spans` is a list of (start,end) seconds to
    sample; None = the whole clip."""
    dur = ff.probe_duration(clip_path)
    if dur <= 0:
        return f"NODUR {clip_path}"
    spans = spans or [(0, dur)]
    pts = []
    for a, b in spans:
        t = a + 2
        while t < b:
            pts.append(t)
            t += sample
    if not pts:
        return f"NOSPANS {clip_path}"
    tmpd = os.path.join(cfg.tmp_dir, "sheet_" + os.path.basename(clip_path))
    os.makedirs(tmpd, exist_ok=True)
    for old in glob.glob(tmpd + "/*.png"):
        os.remove(old)
    got = []
    for i, t in enumerate(pts):
        p = f"{tmpd}/f{i:04d}.png"
        ff.grab_frame(clip_path, t, p, width=thumb_w)
        if os.path.exists(p) and os.path.getsize(p) > 500:
            got.append((t, p))
    if not got:
        return f"NOFRAMES {clip_path}"
    try:
        font = ImageFont.truetype(cfg.font_regular, 22)
    except Exception:
        font = ImageFont.load_default()
    thumbs = []
    for t, p in got:
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        lbl = _mmss(t)
        d.rectangle([4, 4, 4 + len(lbl) * 13 + 8, 30], fill=(0, 0, 0))
        d.text((8, 6), lbl, fill=(255, 255, 0), font=font)
        thumbs.append(im)
    tw, th = thumbs[0].size
    rows = math.ceil(len(thumbs) / cols)
    pad = 4
    board = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * th + (rows + 1) * pad), (255, 255, 255))
    for idx, im in enumerate(thumbs):
        r, c = divmod(idx, cols)
        board.paste(im, (pad + c * (tw + pad), pad + r * (th + pad)))
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    board.save(out_png)
    for _, p in got:
        os.remove(p)
    return f"OK {len(got)} thumbs -> {out_png}"
