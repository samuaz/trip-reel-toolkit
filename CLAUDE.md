# CLAUDE.md — operating manual for an AI assistant driving this toolkit

This repository is a **config-driven toolkit for editing adventure/travel reels**
from multi-camera footage (a POV/helmet cam with a mic + one or more 360
cameras), with an AI-assisted catalog pipeline. It was distilled from a real
long motorcycle trip and **everything below is hard-won**: each "Gotcha" cost a
bad render, a lost moment, or a wrong edit at least once. Treat this file as
pre-loaded training — read it fully before you touch footage.

You (the AI) are expected to do the heavy lifting: catalog the footage, find the
good moments, and assemble reels. The human points you at the footage and
reacts to what you show them. Nothing here is specific to one person or trip —
all paths, cameras and dates live in `config.yaml`.

---

## 0. The golden rules (break these and the edit is wrong)

1. **Verify by WATCHING frames and LISTENING to audio — never by filename or
   metadata.** Before you put a shot in a reel, grab the frame (contact sheet)
   and confirm what is actually there. Pick moments from what you see/hear.
2. **Strict chronological order.** Order beats by real clip time. Out-of-order
   shots are the single most-noticed mistake. Camera clocks can be wrong (see
   Gotcha 11) — order by content/GPS, not blindly by timestamp.
3. **Use every camera AND its audio.** The POV cam has the mic (the rider's
   voice and dialogue). The 360 cameras are NOT mute — they carry ambient/engine
   audio usable as a low bed. Real voice is the spine of the story; music is only
   a bed underneath it (ducked, never on top of speech).
4. **Structure: hook → body → climax → close.** Long shots (8–14s), gradual
   crossfades (never hard cuts), no filler. Let the reel run long while building;
   trim later.
5. **Show the human raw findings as you go.** They steer. Don't batch everything
   to the end.

---

## 1. The pipeline

```
   footage  ──►  CATALOG  ──►  CURATE  ──►  BUILD  ──►  DELIVER
              (describe &     (watch &     (shot     (vertical cut
               detect)         pick)        list)     + music)
```

* **Catalog** — build a searchable description of what's on screen/in the audio:
  * `scripts/transcribe.py` → whisper.cpp SRT per clip (the rider's voice).
  * `scripts/index.py` → Gemini content index per clip (people/animals/signs/
    landmarks/events/hero-shots with timestamps + USE/DISCARD).
  * `scripts/guardrail.py` → **always run after indexing** (see Gotcha 7).
  * `scripts/detect.py` → multi-signal event detector (audio peaks + whisper
    hallucination cross-check) to catch the brief moments catalogs miss.
* **Curate** — `scripts/make_sheets.py` for contact sheets; watch them, decide
  the beats, note exact `ss`/`dur` per shot.
* **Build** — write a reel script (list of shot dicts, see
  `examples/example_reel.py`) and run `scripts/build_reel.py`.
* **Deliver** — `--vertical` adds the "rotate your phone" vertical cut;
  `scripts/gen_music.py` makes music beds.

---

## 2. Gotchas — the pre-loaded lessons (DO NOT re-learn these the hard way)

**1. This ffmpeg may have NO `drawtext`.** Many builds are compiled without it.
All burned-in text is done with **PIL PNG overlays** (`reelkit/text_overlay.py`).
Never add a `drawtext` filter; if you need text, make a PNG and overlay it.

**2. Concatenate with the concat FILTER, not the demuxer.** Action/360 clips
carry a data stream (GPS telemetry) that breaks the concat demuxer. The builder
joins shots with the `xfade`/`acrossfade` filter chain. If you ever concat
manually, use `concat=n=...:v=1:a=1`, not `-f concat`.

**3. The footage disk is the bottleneck and it is flaky.** External drives (esp.
near-full ones) unmount mid-read. Rules: `ffmpeg_workers: 1`; **one heavy disk
read at a time** (don't transcribe and cut simultaneously); make every long job
**resumable** (skip work whose output already exists) and tolerant of the disk
vanishing (exit cleanly, resume later). Keep the drive powered.

**4. Background jobs get killed (~hourly in some agent harnesses).** Long sweeps
must be resumable so relaunching continues where it stopped. Never rely on a
job staying alive; never re-arm automatic pollers without being asked.

**5. whisper HALLUCINATES on noisy/engine/night audio.** Tell-tale: the same
line repeated many times with round timestamps (e.g. a channel sign-off, a city
name, "music"). `reelkit/detect.halluc()` flags runs of ≥5 identical lines.
**Never find a moment from transcription text alone** — cross-check with the
audio-energy peak and the frame.

**6. The filename-suffix trap.** Cameras add suffixes (the reference rig used a
`_D` suffix on POV files). A clip id in a catalog is NOT always the filename. If
you build a path by hand and drop/keep the wrong suffix, ffmpeg silently finds
nothing → empty WAV → false "silent" transcription, or a blank frame. Always
resolve through `cfg.resolve_clip(cam, base)` which tries the configured
extensions, and verify the file exists.

**7. Gemini invents foreign-language signage on dark footage.** It will produce
plausible, real-looking place names in a script that is pure hallucination
(e.g. Chinese signs on footage shot before the trip reached China). Prompt
tuning reduces but does not eliminate it. The fix is **deterministic**: the
`guardrail` neutralises an impossible token class (e.g. CJK characters) in any
catalog file dated before a configured date, and downgrades its USE verdict to
DISCARD. Configure `guardrail` in `config.yaml` and run `scripts/guardrail.py`
after every indexing pass.

**8. Low-res proxies make brief events vanish.** A 1–2s dog/skid disappears at
640p/2fps. Index at **720p / 4fps / MEDIA_RESOLUTION_HIGH**, BRIGHTEN dark
windows before sending (Gemini can't see near-black), and use a prompt that
DEMANDS a per-line list with timestamps — not a vague summary.

**9. 360 cameras: one sphere = several virtual cameras.** With `roll=-90` the
`yaw` axis orbits VERTICALLY, not horizontally — this is the non-obvious bit.
The calibrated angle palette (`config.yaml → angles360`) is: `hero` (3rd-person,
rider level), `front` (road ahead), `dutchL/R` (dynamic diagonal, moving shots
only). Alternate angles from a single clip for "multi-camera" variety. `.insv`
files report duration 0 but `-ss` seeking works.

**10. Color — three situations, three grades (see docs/COLOR_GRADING.md):**
   * POV cam often shoots **D-Log** and comes **underexposed**: you must LIFT
     shadows/mids (a curve that rises), NOT crush them. Crushing is the classic
     mistake (footage ends darker than the raw). → grade `dlog`/`dlogl`.
   * Bright/overexposed day footage: roll OFF the highs so skies don't clip. →
     grade `dlogb`.
   * Night: denoise + lift. → grade `night`. 360 footage is usually NOT log → a
     soft `nat`/`lift`.

**11. Camera clocks can be reset/wrong.** A camera that lost its clock stamps
files with a bogus date. The data is intact — order by GPS/content, not by the
timestamp. Don't trust a catalog window's `mm:ss` as the exact action time
either; it can drift. Verify the exact second on a frame.

**12. Some clips are simply corrupt** (a few hundred KB, unplayable). Skip them;
don't burn time trying to recover.

**13. Blur number plates / faces where needed**, and **re-check after the grade**
(a lift can make a plate readable again). Shots support a `blur` list of boxes.

**14. Keep deliverables under platform limits.** For sharing previews, 720p
keeps files small; the master stays 1080p in the output folder.

---

## 3. Module map

```
reelkit/
  config.py        load config.yaml; resolve cameras, grades, 360 angles, fonts
  ffmpeg_helpers.py probe/run wrappers + the encoder constants & WAV/frame grab
  text_overlay.py  PIL subtitle/title/card PNGs (because no drawtext)
  reframe360.py    v360 angle filter from the calibrated palette
  builder.py       render_shot() + assemble() — crossfades + ducked music bed
  vertical.py      "rotate your phone" 1080x1920 export
  transcribe.py    whisper.cpp -> SRT (resumable)
  detect.py        audio-peak + whisper-hallucination event detector
  index_ai.py      Gemini per-window content index (bright/HIGH/strict prompt)
  guardrail.py     deterministic anti-hallucination neutraliser
  sheets.py        contact-sheet grids
  trim.py          lossless keep-spans trimming
  audio.py         demucs voice removal / lowpass censor windows
  music.py         Lyria instrumental generation

scripts/           thin CLIs over the above (run these)
wizard.py          interactive configurator -> config.yaml
examples/          a worked reel script
docs/              deeper notes on cameras+audio, color, event detection
```

## 4. Extending it

* **New camera** → add an entry under `cameras:` in `config.yaml` (name, path,
  type, has_mic, extensions). Reference the name in shots.
* **New grade** → add a named ffmpeg filter chain under `grades:`.
* **New 360 angle** → add `name: [yaw, pitch, roll]` under `angles360:`.
* **A reel** → copy `examples/example_reel.py`, edit the `SHOTS` list.

## 5. First-run checklist for the AI

0. **Run `python3 scripts/doctor.py` first.** It reports every dependency as OK
   / MISS / opt with a copy-paste fix command, and exits non-zero if a CORE dep
   is missing. Install the MISS items (or run `./setup.sh`), then re-run it.
   Core = ffmpeg + PyYAML + Pillow; the rest (whisper / google-genai +
   GEMINI_API_KEY / demucs) only unlock transcription, AI indexing and audio
   cleanup respectively, and are installed from `requirements-optional.txt`.
1. Confirm `config.yaml` exists (`python3 wizard.py` if not) and the camera
   paths resolve. Test with `scripts/make_sheets.py`.
2. Transcribe + index a day of footage; run the guardrail; run the detector.
3. Watch contact sheets, pick beats in chronological order, note ss/dur.
4. Write a reel script; build; watch frames of the output; iterate.
5. Produce the vertical cut and show the human.
