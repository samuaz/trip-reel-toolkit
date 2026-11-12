# Event detection & cataloging

The problem: you can't find every good moment by eye (hours of footage) and you
can't trust a single automatic signal. So the catalog combines several, and you
always finish by **watching the frame**.

## Why no single signal is enough
- **whisper text** alone → hallucinates on engine/wind/night audio (repeated
  identical lines with round timestamps). Great for real speech, dangerous as a
  moment-finder.
- **evenly-spaced frame sheets** alone → a 1–2s event (a dog, a skid) falls
  between samples, especially in the dark.
- **Gemini index** alone → misses brief events at low res and invents foreign
  signage on dark footage.

## The multi-signal detector (`scripts/detect.py`)
1. **Audio energy** in the bark/voice band (700–4500 Hz): peaks = dogs, shouts,
   braking, horns. Two thresholds (strong/weak) off the median + MAD.
2. **Hallucination ranges**: runs of ≥5 identical consecutive SRT lines =
   transcription unreliable there.
3. **Cross**: a strong audio peak INSIDE a hallucinated range = **review this** —
   something happened and the text is garbage. This is exactly how the "dogs at
   night" type of moment surfaces when both AIs missed it.

## AI content index (`scripts/index.py`)
- Proxy at **720p / 4fps / MEDIA_RESOLUTION_HIGH** (low-res proxies lose brief
  events).
- **Brighten dark windows** before sending (the model can't see near-black).
- Prompt **demands** a per-line list with `mm:ss-mm:ss | TYPE | description |
  USE/DISCARD`, not a vague summary.
- **Always run `scripts/guardrail.py` afterwards** (see below).

## The guardrail (`scripts/guardrail.py`)
Gemini will produce plausible, real-looking foreign signage that is pure
hallucination (e.g. Chinese place names before the trip reached China). Prompt
tuning is not enough. The guardrail is **deterministic**: a token class (regex,
e.g. CJK) is only legitimate from a configured date onward; in any earlier
catalog file it is neutralised to "illegible" and its USE verdict is downgraded
to DISCARD. Configure under `config.yaml → guardrail`. Run after every index
pass (dry-run first, then `--apply`).

## Discipline
- A catalog window's `mm:ss` is an approximate anchor, not the exact action
  time — it can drift. Confirm the precise second on a frame.
- Verdicts (USE/DISCARD) are hints. The human + a watched frame decide.
