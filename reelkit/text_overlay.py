"""Burned-in text (subtitles, titles, cards) rendered with PIL, because this
toolkit assumes ffmpeg has NO `drawtext` filter.

A subtitle is drawn as a transparent full-canvas PNG (soft shadow + white text
with a dark stroke) that the builder overlays for a time range. Titles and
cards are full opaque frames turned into short video segments.

All sizes scale off the configured canvas, so the same code works at 1920x1080
or any other resolution.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CREAM = (235, 225, 190)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _spaced(draw, text, font, y, canvas_w, sp, fill, stroke_w, stroke_fill):
    """Draw letter-spaced, horizontally-centered text. Returns total width."""
    widths = [draw.textlength(c, font=font) for c in text]
    total = sum(widths) + sp * (len(text) - 1)
    x = (canvas_w - total) / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)
        x += w + sp
    return total


def _fit_lines(text, font_path, maxw, sp):
    """Pick the largest font size (46..28) that fits `text` on 1-2 centered
    lines within maxw. Returns (size, [lines])."""
    up = text.upper()
    words = up.split()
    for size in range(46, 27, -2):
        f = _font(font_path, size)
        wl = lambda s: sum(f.getlength(c) for c in s) + sp * max(0, len(s) - 1)
        if wl(up) <= maxw:
            return size, [up]
        best = None
        for i in range(1, len(words)):
            l1, l2 = " ".join(words[:i]), " ".join(words[i:])
            if wl(l1) <= maxw and wl(l2) <= maxw:
                dd = abs(wl(l1) - wl(l2))
                if best is None or dd < best[0]:
                    best = (dd, l1, l2)
        if best:
            return size, [best[1], best[2]]
    return 28, [up]


def subtitle_png(cfg, txt, path):
    """Write a transparent canvas-sized PNG with a centered lower-third caption."""
    W, H = cfg.W, cfg.H
    sp, maxw = 4, int(W * 0.90)
    size, lines = _fit_lines(txt, cfg.font_regular, maxw, sp)
    f = _font(cfg.font_regular, size)
    lh = size + 12
    y0 = int(H * 0.85) - (len(lines) - 1) * lh
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    for k, ln in enumerate(lines):
        _spaced(ds, ln, f, y0 + k * lh + 2, W, sp, (0, 0, 0, 205), 0, (0, 0, 0, 0))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k, ln in enumerate(lines):
        _spaced(d, ln, f, y0 + k * lh, W, sp, (255, 255, 255, 255), 2, (0, 0, 0, 225))
    Image.alpha_composite(shadow, layer).save(path)


def title_png(cfg, title, subtitle, path):
    """Opaque title frame (big centered title + rule + subtitle)."""
    W, H = cfg.W, cfg.H
    im = Image.new("RGB", (W, H), (8, 8, 10))
    d = ImageDraw.Draw(im)
    _spaced(d, title.upper(), _font(cfg.font_bold, int(H * 0.118)), H // 2 - 120, W, 12,
            (255, 255, 255, 255), 4, (0, 0, 0, 220))
    d.rectangle([W // 2 - 150, H // 2 + 40, W // 2 + 150, H // 2 + 44], fill=CREAM)
    if subtitle:
        _spaced(d, subtitle.upper(), _font(cfg.font_regular, 40), H // 2 + 70, W, 8,
                CREAM, 2, (0, 0, 0, 180))
    im.save(path)


def card_png(cfg, main, sub, path):
    """Opaque end/transition card (e.g. 'TO BE CONTINUED')."""
    W, H = cfg.W, cfg.H
    im = Image.new("RGB", (W, H), (8, 8, 10))
    d = ImageDraw.Draw(im)
    _spaced(d, main.upper(), _font(cfg.font_bold, int(H * 0.083)), H // 2 - 70, W, 8,
            (255, 255, 255, 255), 3, (0, 0, 0, 210))
    if sub:
        d.rectangle([W // 2 - 110, H // 2 + 22, W // 2 + 110, H // 2 + 26], fill=CREAM)
        _spaced(d, sub.upper(), _font(cfg.font_regular, 34), H // 2 + 56, W, 6,
                CREAM, 2, (0, 0, 0, 180))
    im.save(path)
