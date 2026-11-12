"""Load and resolve config.yaml into a convenient object.

Nothing here touches the network or your footage; it only reads the YAML,
expands ~ in paths, auto-detects fonts when you left them blank, and gives the
rest of the toolkit one place to ask "where is camera X?" / "what is grade Y?".
"""
import os
import re
import glob
import yaml

# Fonts we try, in order, when the user left fonts.bold / fonts.regular blank.
# Covers macOS, common Linux (DejaVu/Liberation) and Windows.
_FONT_CANDIDATES = {
    "bold": [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
    "regular": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
}


def _expand(p):
    return os.path.expanduser(p) if isinstance(p, str) and p else p


def _first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def _secure_dir(path):
    """Create a private (0700) directory for render/temp files. If it already
    exists, refuse to use it unless the current user owns it and it is not
    group/world-writable (avoids cache poisoning / symlink clobber on shared
    machines where /tmp is world-writable)."""
    if os.path.exists(path):
        st = os.stat(path)
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            raise SystemExit(f"refusing to use tmp_dir not owned by you: {path}")
        if st.st_mode & 0o022:
            raise SystemExit(f"refusing to use group/world-writable tmp_dir: {path} "
                             f"(run: chmod 700 {path})")
    else:
        os.makedirs(path, mode=0o700, exist_ok=True)
    return path


class Camera:
    def __init__(self, name, d):
        self.name = name
        self.path = _expand(d.get("path", ""))
        self.type = d.get("type", "pov")          # pov | sphere360 | photo
        self.has_mic = bool(d.get("has_mic", False))
        self.extensions = d.get("extensions", ["MP4", "mp4"])

    def resolve(self, base):
        """Find the real file for a clip `base` (name without extension).

        `base` may also be an absolute path or a path with extension, in which
        case it is returned as-is if it exists. Returns None if not found.
        """
        if os.path.isabs(base) and os.path.exists(base):
            return base
        direct = os.path.join(self.path, base)
        if os.path.exists(direct):
            return direct
        for ext in self.extensions:
            cand = os.path.join(self.path, f"{base}.{ext}")
            if os.path.exists(cand):
                return cand
        # last resort: glob (handles unexpected casing)
        hits = glob.glob(os.path.join(self.path, base + ".*"))
        return hits[0] if hits else None


class Config:
    def __init__(self, data):
        self._d = data
        proj = data.get("project", {})
        self.name = proj.get("name", "My Trip")
        self.output_dir = _expand(proj.get("output_dir", "~/trip-reels/output"))
        self.tmp_dir = _expand(proj.get("tmp_dir", "~/.cache/trip-reel-toolkit"))

        c = data.get("canvas", {})
        self.W = int(c.get("width", 1920))
        self.H = int(c.get("height", 1080))
        self.FPS = int(c.get("fps", 30))
        self.XF = float(c.get("crossfade", 0.45))

        self.cameras = {n: Camera(n, d) for n, d in data.get("cameras", {}).items()}

        f = data.get("fonts", {})
        self.font_bold = _expand(f.get("bold")) or _first_existing(_FONT_CANDIDATES["bold"])
        self.font_regular = _expand(f.get("regular")) or _first_existing(_FONT_CANDIDATES["regular"])

        self.grades = data.get("grades", {})
        self.angles360 = {k: tuple(v) for k, v in data.get("angles360", {}).items()}
        self.fov = data.get("reframe360_fov", {"ih_fov": 193, "iv_fov": 193, "h_fov": 150, "v_fov": 85})

        a = data.get("audio", {})
        self.voice_filter = a.get("voice_filter", "loudnorm=I=-11:TP=-1.3:LRA=10")
        self.ambient_filter = a.get("ambient_filter", "loudnorm=I=-20:TP=-2:LRA=12")
        self.music_volume = float(a.get("music_volume", 0.20))
        self.duck = a.get("duck", {"threshold": 0.02, "ratio": 14, "attack": 8, "release": 360})
        self.music_dir = _expand(a.get("music_dir", "~/trip-reels/music"))
        self.default_music = a.get("default_music", "")

        t = data.get("tools", {})
        self.whisper_cli = _expand(t.get("whisper_cli", ""))
        self.whisper_model = _expand(t.get("whisper_model", ""))
        self.whisper_lang = t.get("whisper_lang", "en")
        self.ffmpeg_workers = int(t.get("ffmpeg_workers", 1))

        ai = data.get("ai", {})
        self.gemini_model = ai.get("gemini_model", "gemini-3.6-flash")
        self.lyria_model = ai.get("lyria_model", "models/lyria-3.5")
        self.index_window_s = int(ai.get("index_window_s", 120))
        self.index_fps = int(ai.get("index_fps", 4))
        self.index_px = int(ai.get("index_px", 720))

        g = data.get("guardrail", {})
        self.guard_token_regex = g.get("token_regex", "")
        self.guard_from_date = str(g.get("allowed_from_date", "99999999"))
        self.guard_filename_date = g.get("filename_date_regex", r"(20\d{6})")

        _secure_dir(self.tmp_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    # -- helpers -------------------------------------------------------------
    def camera(self, name):
        if name not in self.cameras:
            raise KeyError(f"camera '{name}' not in config (have: {list(self.cameras)})")
        return self.cameras[name]

    def resolve_clip(self, camera_name, base):
        return self.camera(camera_name).resolve(base)

    def grade(self, name):
        if not name:
            return None
        if name not in self.grades:
            raise KeyError(f"grade '{name}' not in config (have: {list(self.grades)})")
        return self.grades[name]

    def music_path(self, name=None):
        name = name or self.default_music
        if not name:
            return None
        if os.path.isabs(name):
            return name
        return os.path.join(self.music_dir, name)

    def gemini_key(self):
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def find_config(explicit=None):
    """Locate config.yaml: explicit arg, $REELKIT_CONFIG, or ./config.yaml."""
    for cand in (explicit, os.environ.get("REELKIT_CONFIG"), "config.yaml",
                 os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")):
        if cand and os.path.exists(cand):
            return cand
    return None


def load(path=None):
    cfg_path = find_config(path)
    if not cfg_path:
        raise SystemExit(
            "No config.yaml found. Run `python3 wizard.py` to create one, "
            "or set REELKIT_CONFIG=/path/to/config.yaml"
        )
    with open(cfg_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return Config(data)
