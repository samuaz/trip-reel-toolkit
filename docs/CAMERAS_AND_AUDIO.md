# Cameras & audio

## The cameras

- **POV / helmet cam** (`type: pov`): flat 16:9, carries the **mic** — the
  rider's voice and any dialogue. This is the source of the story's narration.
  Crop to the canvas; grade for D-Log/underexposure (see COLOR_GRADING.md).
- **360 cameras** (`type: sphere360`): dual-fisheye. Reframed into flat virtual
  cameras with ffmpeg's `v360`. They are **NOT mute** — they record ambient /
  engine audio you can use as a low bed. Give 3rd-person perspective.

## 360 reframing — the one non-obvious thing

A single 360 sphere becomes several "cameras" by changing yaw/pitch/roll. The
trap: **with `roll=-90` the `yaw` axis orbits VERTICALLY, not horizontally.**
That's why the calibrated palette moves pitch/roll the way it does. Defaults
(verified frame-by-frame; in `config.yaml → angles360`):

| Angle  | yaw | pitch | roll | Use |
|--------|-----|-------|------|-----|
| hero   | 180 | -8 | -90  | classic 3rd person (rider, level) — people/interaction |
| front  | 0   | -8 | +90  | the road ahead (POV off the selfie stick) |
| dutchL | 180 | -8 | -50  | dynamic diagonal — **moving shots only** |
| dutchR | 180 | -8 | -130 | dynamic diagonal — **moving shots only** |

Base FOV: `ih_fov=iv_fov=193`, `h_fov=150`, `v_fov=85`. Alternate front↔hero↔dutch
from one clip for cheap "multi-camera" variety. `.insv` files report duration 0
in metadata but `-ss` seeking works.

## Audio philosophy

- **Voice is the spine.** Prioritise the POV mic. When you cut to a 360 shot
  during a line of dialogue, keep the POV audio with `audio_from` so the voice
  stays continuous while the picture changes.
- **Music is a bed, not a layer on top of speech.** The builder side-chain
  **ducks** the music under the program audio automatically.
- The 360's own audio is a **low ambient bed** (engine/wind), filtered with the
  `ambient_filter`; the POV voice uses the stronger `voice_filter`
  (highpass + compressor + presence EQ + loudnorm).

## Cleaning swearing / unwanted voice (optional)

`reelkit/audio.py`, chosen by how loud the engine is:

- **Strong engine** (offroad): demucs two-stem separation, keep the `no_vocals`
  stem → voice gone, engine + ambience remain.
- **Weak engine** (idle/dusk): demucs leaves the stem nearly silent, so instead
  `lowpass=f=150` ONLY over the offending window (a low rumble; engine stays).
