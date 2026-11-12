# Color grading

Grades are named ffmpeg `-vf` filter chains in `config.yaml → grades`. You
reference a grade by name from a shot (`"grade": "dlog"`). Tune the numbers to
your camera; the shapes below are the lessons.

## Three situations, three grades

### 1. Underexposed D-Log (POV cam) → LIFT, don't crush
Many action cams shoot a flat **D-Log** profile and come **underexposed**. The
fix is a curve that **raises** shadows and mids toward Rec.709 while keeping the
highs. The classic mistake is a curve that *lowers* the low end (e.g. mapping
0→0.03 with a dip) — it crushes the image darker than the raw. Verify on a frame
that faces/skies/signs became legible.

```
dlog:  curves=all='0/0.03 0.10/0.24 0.30/0.50 0.55/0.70 0.85/0.92 1/1',eq=contrast=1.04:saturation=1.30:gamma=1.22
dlogl: (stronger lift for extreme/interior shots)
```

### 2. Bright / overexposed day → roll OFF the highs
Well-lit overcast days can clip skies. `dlogb` keeps the mids but hard-rolls the
highs down so skies don't blow out.

```
dlogb: curves=all='0/0.03 0.35/0.37 0.60/0.60 0.80/0.64 1/0.78',eq=contrast=1.03:saturation=1.20:gamma=1.08
```

### 3. Night → denoise + lift
Night footage is usually just underexposed Rec.709 (not log). Denoise the grain,
then lift.

```
night: hqdn3d=4:3:6:4,eq=brightness=0.14:gamma=1.6:contrast=1.05
```

### 360 footage
Usually **not** log → a soft `nat` (gentle contrast/saturation) keeps it natural;
use `lift` only for dark 360 (e.g. interiors/garages).

## Rules of thumb
- Grade **per shot**, not globally — a lift that saves a dark valley shot will
  wash out one that already had good light.
- **Re-check number-plate/face blurs after grading** — a lift can make a blurred
  plate readable again.
- Always confirm the result by looking at an actual frame, measuring luma if you
  can, not by eyeballing the filter string.
