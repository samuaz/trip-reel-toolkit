"""Audio cleanup: remove the rider's swearing/voice while keeping engine,
dogs, wind and ambience.

Two strategies, chosen by how loud the engine is in the shot:

  * STRONG engine (offroad): run demucs voice separation and keep the
    `no_vocals` stem -> the voice is gone, engine + ambience remain.
  * WEAK engine (idle / dusk): demucs leaves the stem nearly silent, so instead
    apply a `lowpass=f=150` ONLY over the offending window -> a low rumble, the
    engine stays. Use `censor_window_filter()` to build the ffmpeg -af string.

demucs is optional (pip install demucs soundfile). If it isn't installed,
`separate_novocals` raises a clear error.
"""
import os
import glob
import subprocess
from . import ffmpeg_helpers as ff


def separate_novocals(wav_path, out_dir):
    """Run demucs two-stem separation; return the path to the no_vocals stem."""
    try:
        subprocess.run(["python3", "-m", "demucs", "--two-stems=vocals", "-o", out_dir, wav_path],
                       check=True, timeout=3600)
    except FileNotFoundError:
        raise RuntimeError("demucs not installed. Run: pip3 install --user demucs soundfile")
    hits = glob.glob(os.path.join(out_dir, "*", "*", "no_vocals.wav"))
    if not hits:
        raise RuntimeError("demucs produced no no_vocals stem")
    return hits[0]


def extract_and_separate(cfg, cam_name, src_base, out_dir):
    """Extract a clip's audio to WAV and separate it. Returns no_vocals path."""
    os.makedirs(out_dir, exist_ok=True)
    src = cfg.camera(cam_name).resolve(src_base)
    if not src:
        raise FileNotFoundError(f"{cam_name}:{src_base}")
    wav = os.path.join(out_dir, f"{src_base}.wav")
    ff.extract_wav(src, wav, sr=44100, mono=False)
    return separate_novocals(wav, out_dir)


def censor_window_filter(windows, freq=150):
    """Build an ffmpeg -af value that lowpass-filters only the given windows.
    windows: list of (t_start, t_end) in seconds."""
    if not windows:
        return None
    enables = "+".join(f"between(t,{a},{b})" for a, b in windows)
    return f"lowpass=f={freq}:enable='{enables}'"
