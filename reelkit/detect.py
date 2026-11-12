"""Multi-signal event detector — finds moments the catalog would otherwise miss.

Why this exists: you cannot trust whisper text alone (it hallucinates on noisy
night/engine audio) nor evenly-spaced frame sheets (they skip 1-2s events in the
dark). So we combine three signals:

  1) AUDIO: listen to the bark/voice band (700-4500 Hz) and mark energy PEAKS
     (dogs, shouts, braking, horns). Two thresholds: strong and weak.
  2) HALLUCINATION: runs of identical consecutive SRT lines => transcription is
     unreliable there (review by audio/vision).
  3) CROSS: an audio peak INSIDE a hallucinated range = high priority
     ("something happened and the text is garbage") -> prime reel candidate.

Optional MOTION signal (scene-change on a brightened proxy) is noisy on shaky
offroad footage; enable only for stable shots.
"""
import os
import re
import struct
import tempfile
import statistics
import subprocess


def _audio_env(clip, sr=4000):
    fd, raw = tempfile.mkstemp(suffix=".raw")
    os.close(fd)
    try:
        r = subprocess.run(["ffmpeg", "-y", "-i", clip, "-vn", "-af",
                            "highpass=f=700,lowpass=f=4500,aresample=%d" % sr, "-ac", "1", "-f", "s16le", raw],
                           stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=1200)
        if r.returncode != 0 or not os.path.exists(raw):
            return []
        data = open(raw, "rb").read()
    finally:
        try:
            os.remove(raw)
        except OSError:
            pass
    n = len(data) // 2
    vals = struct.unpack("<%dh" % n, data[:n * 2])
    env = []
    for i in range(0, n - sr, sr):
        seg = vals[i:i + sr]
        env.append((i / sr, (sum(x * x for x in seg) / sr) ** 0.5))
    return env


def _peaks(env):
    if not env:
        return [], 0, 0
    r = [e[1] for e in env]
    med = statistics.median(r)
    mad = statistics.median([abs(x - med) for x in r]) or 1.0
    strong_t, weak_t = med + 4 * mad, med + 2.5 * mad
    ev = []
    for t, v in env:
        lvl = "STRONG" if v > strong_t else ("weak" if v > weak_t else None)
        if lvl:
            ev.append((t, v, lvl))
    groups = []
    for t, v, lvl in ev:
        if groups and t - groups[-1][-1][0] <= 2:
            groups[-1].append((t, v, lvl))
        else:
            groups.append([(t, v, lvl)])
    out = []
    for g in groups:
        tp, vp, _ = max(g, key=lambda x: x[1])
        strong = any(x[2] == "STRONG" for x in g)
        out.append((g[0][0], g[-1][0], tp, vp, strong))
    return out, med, mad


def halluc(srt):
    """Return ranges (start_s, end_s, sample) where >=5 identical SRT lines
    repeat consecutively => whisper hallucination."""
    if not srt or not os.path.exists(srt):
        return []

    def to_s(ts):
        h, m, rest = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + int(rest.split(",")[0])

    cur, seq = None, []
    for ln in open(srt, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        m = re.match(r"(\d{2}:\d{2}:\d{2}),\d+ -->", ln)
        if m:
            cur = to_s(m.group(1))
        elif ln and cur is not None and not ln.isdigit() and "-->" not in ln:
            seq.append((cur, ln))
            cur = None
    ranges, i = [], 0
    while i < len(seq):
        j = i
        while j + 1 < len(seq) and seq[j + 1][1] == seq[i][1]:
            j += 1
        if j - i >= 4:
            ranges.append((seq[i][0], seq[j][0], seq[i][1][:40]))
        i = j + 1
    return ranges


def analyze(clip, srt=None):
    env = _audio_env(clip)
    ev, med, mad = _peaks(env)
    hal = halluc(srt)

    def hms(s):
        return f"{int(s)//60:02d}:{int(s)%60:02d}"

    lines = [f"# {os.path.basename(clip)}  baseline={med:.0f} MAD={mad:.0f}"]
    lines.append(f"# whisper hallucination (text UNRELIABLE) in {len(hal)} ranges:")
    for a, b, txt in hal:
        lines.append(f"   {hms(a)}-{hms(b)}  \"{txt}...\"")
    lines.append("# AUDIO EVENTS (bark/voice band peaks):")
    for a, b, tp, vp, strong in ev:
        inhal = any(ra <= tp <= rb for ra, rb, _ in hal)
        tag = ("*STRONG" if strong else ".weak") + ("  <-REVIEW (garbage text + event)" if inhal and strong else "")
        lines.append(f"   {hms(a)}-{hms(b)} peak {hms(tp)} RMS={vp:.0f}  {tag}")
    return "\n".join(lines), {"events": ev, "halluc": hal, "median": med, "mad": mad}
