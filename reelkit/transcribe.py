"""Transcribe a clip's voice with whisper.cpp (local, free).

Writes an .srt next to a cache dir. Lessons baked in:
  * whisper HALLUCINATES on noisy/engine audio: repeated identical lines with
    round timestamps are noise, not speech. detect_events.halluc() flags these;
    don't trust transcription alone to find moments.
  * Always use the REAL file path. Camera naming traps (e.g. a DJI `_D` suffix)
    silently yield an empty WAV and a false "silent" result.
"""
import os
import subprocess
from . import ffmpeg_helpers as ff


def transcribe_clip(cfg, src, srt_out, ss=0, dur=None):
    """Produce an .srt for `src` via whisper.cpp. Returns srt_out or None.
    Skips work if the srt already exists (resumable sweeps)."""
    if not cfg.whisper_cli or not cfg.whisper_model:
        raise RuntimeError("tools.whisper_cli / tools.whisper_model not set in config.yaml")
    if os.path.exists(srt_out):
        return srt_out
    os.makedirs(os.path.dirname(srt_out) or ".", exist_ok=True)
    wav = os.path.join(cfg.tmp_dir, "_tx.wav")
    if ff.extract_wav(src, wav, ss=ss, dur=dur).returncode != 0 or not os.path.exists(wav):
        return None
    stem = os.path.splitext(srt_out)[0]
    tmp_stem = stem + ".tmp"      # whisper appends .srt; write atomically
    subprocess.run([cfg.whisper_cli, "-m", cfg.whisper_model, "-l", cfg.whisper_lang,
                    "-t", "10", "-osrt", "-of", tmp_stem, "-f", wav],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3600)
    try:
        os.remove(wav)
    except OSError:
        pass
    if os.path.exists(tmp_stem + ".srt"):
        os.replace(tmp_stem + ".srt", srt_out)
        return srt_out
    return None
