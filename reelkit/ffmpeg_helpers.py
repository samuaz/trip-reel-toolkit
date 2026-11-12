"""Thin wrappers around ffmpeg/ffprobe plus shared render constants.

Lessons baked in here:
  * This toolkit never relies on ffmpeg's `drawtext` filter — many builds are
    compiled without it. Text is burned via PIL PNG overlays (see text_overlay).
  * Clips from action/360 cameras often carry a data stream (GPS telemetry)
    that breaks the concat *demuxer*. We always concatenate with the concat
    *filter* instead (see builder.assemble).
  * Audio is mapped with `0:a:0?` (the `?` makes it optional) so a silent clip
    doesn't abort the render.
"""
import os
import subprocess

# Standard encoder settings for intermediate render segments.
SEG_VCODEC = ["-c:v", "libx264", "-crf", "20", "-preset", "veryfast"]
SEG_ACODEC = ["-c:a", "aac", "-ar", "48000"]
# Final master is a touch higher quality.
FINAL_VCODEC = ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p"]
FINAL_ACODEC = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]


def run(args, timeout=600, quiet=True):
    """Run ffmpeg/ffprobe. Returns the CompletedProcess."""
    err = subprocess.DEVNULL if quiet else subprocess.PIPE
    return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=err, timeout=timeout)


def probe_duration(path):
    """Duration in seconds (float), or 0.0 if unknown."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", path],
        capture_output=True, text=True, timeout=60)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def ok_file(path, min_bytes=10000):
    """A render segment is considered valid if it exists and isn't a stub."""
    return os.path.exists(path) and os.path.getsize(path) > min_bytes


def extract_wav(src, dst, ss=0, dur=None, sr=16000, mono=True, extra_af=None):
    """Extract audio to WAV (for whisper / analysis). `-nostdin` + `-v error`
    so it fails loudly but doesn't hang waiting on input."""
    args = ["ffmpeg", "-nostdin", "-v", "error"]
    if ss:
        args += ["-ss", str(ss)]
    args += ["-i", src]
    if dur:
        args += ["-t", str(dur)]
    args += ["-vn"]
    if mono:
        args += ["-ac", "1"]
    args += ["-ar", str(sr)]
    if extra_af:
        args += ["-af", extra_af]
    args += ["-y", dst]
    return run(args, timeout=1200)


def grab_frame(src, ss, dst, width=None):
    """Grab a single frame at time `ss`. Use the real file path (watch out for
    camera suffixes like `_D` on DJI files — a wrong name silently yields no
    frame)."""
    vf = f"scale={width}:-2" if width else None
    args = ["ffmpeg", "-y", "-ss", str(ss), "-i", src, "-map", "0:V:0", "-frames:v", "1"]
    if vf:
        args += ["-vf", vf]
    args += [dst]
    return run(args, timeout=60)
