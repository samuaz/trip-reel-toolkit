"""Lossless trim: keep only chosen spans of a long clip, stream-copied.

`-c copy` is fast and lossless but snaps to keyframes, so cuts land on the
nearest keyframe (fine for making lighter "selects" from huge originals). The
original is never modified; output is validated with ffprobe.
"""
import os
import uuid
import shutil
import subprocess
from . import ffmpeg_helpers as ff


def merge_spans(spans, pad=3, gap_merge=8):
    """Pad each span and merge spans closer than gap_merge seconds."""
    spans = sorted([max(0, a - pad), b + pad] for a, b in spans)
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1] + gap_merge:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def trim_keep(clip_path, spans, out_path):
    """Keep `spans` (list of (start,end) seconds), lossless. Returns status str."""
    if not os.path.exists(clip_path):
        return f"NOFILE {clip_path}"
    if not spans:
        return "NOSPANS"
    total = ff.probe_duration(clip_path)
    keep_dur = sum(b - a for a, b in spans)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tmp, parts = [], []
    try:
        for a, b in spans:
            p = f"/tmp/trim_{uuid.uuid4().hex}.mp4"
            tmp.append(p)
            r = subprocess.run(["ffmpeg", "-y", "-ss", str(a), "-to", str(b), "-i", clip_path,
                                "-c", "copy", "-avoid_negative_ts", "make_zero", p],
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=300)
            if r.returncode == 0 and ff.ok_file(p, 1000):
                parts.append(p)
        if not parts:
            return "FAIL_PARTS"
        if len(parts) == 1:
            shutil.copy(parts[0], out_path)
        else:
            lst = f"/tmp/concat_{uuid.uuid4().hex}.txt"
            tmp.append(lst)
            # concat demuxer list: paths are our own /tmp files (no quotes needed)
            open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                            "-c", "copy", out_path],
                           stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=300)
        if not ff.ok_file(out_path):
            return "FAIL_OUT"
        od = ff.probe_duration(out_path)
        ok = od > 0 and abs(od - keep_dur) <= max(15, 0.25 * keep_dur)
        return (f"OK  orig={total:.0f}s -> {od:.0f}s (expected ~{keep_dur:.0f}s)"
                if ok else f"BAD_DUR got {od:.0f}s expected ~{keep_dur:.0f}s")
    finally:
        for p in tmp:
            try:
                os.remove(p)
            except OSError:
                pass
