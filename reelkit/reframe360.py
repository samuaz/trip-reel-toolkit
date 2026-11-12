"""Reframe a 360 sphere into a flat virtual camera with ffmpeg's `v360`.

THE ONE THING TO KNOW (verified frame-by-frame, see docs/CAMERAS_AND_AUDIO.md):
with roll=-90 the `yaw` axis orbits VERTICALLY, not horizontally. That is why
the default angle palette uses roll=-90/+90 and moves pitch/yaw accordingly:

    hero   yaw=180 pitch=-8 roll=-90   -> classic 3rd person (rider, level)
    front  yaw=0   pitch=-8 roll=+90   -> the road ahead (POV off the stick)
    dutchL/R roll=-50 / -130           -> dynamic diagonal (moving shots only)

`.insv` files report duration 0 in metadata but `-ss` seeking works fine.
"""


def v360_filter(cfg, yaw, pitch, roll):
    f = cfg.fov
    return (f"v360=dfisheye:e:ih_fov={f['ih_fov']}:iv_fov={f['iv_fov']}:"
            f"yaw={yaw}:pitch={pitch}:roll={roll}:"
            f"h_fov={f['h_fov']}:v_fov={f['v_fov']}:w={cfg.W}:h={cfg.H}")


def angle_filter(cfg, angle_name):
    """Return the v360 filter string for a named angle from the config palette."""
    if angle_name not in cfg.angles360:
        raise KeyError(f"360 angle '{angle_name}' not in config (have: {list(cfg.angles360)})")
    yaw, pitch, roll = cfg.angles360[angle_name]
    return v360_filter(cfg, yaw, pitch, roll)
