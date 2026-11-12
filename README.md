# trip-reel-toolkit

A config-driven toolkit for turning multi-camera adventure footage (a POV/helmet
cam with a mic + one or more 360 cameras) into polished travel **reels** — with
an AI-assisted catalog pipeline so you can find the good moments without
re-watching hours of video.

It is built to be driven by an **AI coding assistant** (Claude, Cursor, Copilot,
…). The assistant reads [`CLAUDE.md`](./CLAUDE.md), which carries all the
hard-won lessons as pre-loaded "training", and does the heavy lifting; you point
it at your footage and react to what it shows you.

## What it does

- **Builds reels** from a simple shot list: crossfades (never hard cuts),
  burned-in captions, titles/cards, color grades, a side-chain-ducked music bed,
  and a vertical "rotate your phone" cut for Instagram/TikTok.
- **Reframes 360 footage** into several virtual cameras (hero / road-ahead /
  dutch) from one sphere, with a pre-calibrated angle palette.
- **Catalogs footage with AI**: whisper.cpp transcription + Gemini content
  indexing (people, animals, signs, landmarks, events, hero shots) + a
  multi-signal event detector that catches the brief moments.
- **Guards against AI hallucination** with a deterministic post-processor.
- **Cleans audio** (optional demucs voice removal / lowpass censor windows).

## Requirements

- **ffmpeg + ffprobe** (system): `brew install ffmpeg` / `apt install ffmpeg`.
- **Python 3.9+**: `pip3 install -r requirements.txt`
  (core is just PyYAML + Pillow; the rest is optional).
- Optional **whisper.cpp** for local transcription: `brew install whisper-cpp`
  (gives `whisper-cli`) + a model file (e.g. `ggml-large-v3-turbo-q5_0.bin`).
- Optional **GEMINI_API_KEY** in your environment for AI indexing + music.

## Setup

The easy path — one script, then the wizard:

```bash
./setup.sh                   # venv + core deps; installs ffmpeg via brew on macOS
source .venv/bin/activate
python3 wizard.py            # interactive: asks for folders, cameras, tools...
```

Or do it by hand:

```bash
pip3 install -r requirements.txt            # core (PyYAML + Pillow — light)
# optional features, only if you want them:
pip3 install -r requirements-optional.txt   # AI indexing + music + demucs
python3 wizard.py
```

**Not sure what's installed?** Run the doctor — it prints exactly what is
present and the copy-paste command to fix anything missing (great for letting
an AI assistant bootstrap the repo itself):

```bash
python3 scripts/doctor.py
```

The wizard writes `config.yaml` (your personal, git-ignored config). It starts
from `config.example.yaml` so you keep the tuned color grades, 360 angles and
audio filters, and only asks for what's specific to you.

### What needs installing

| Dependency | Required? | Install |
|------------|-----------|---------|
| ffmpeg + ffprobe | yes | `brew install ffmpeg` / `apt install ffmpeg` |
| PyYAML + Pillow | yes | `pip3 install -r requirements.txt` |
| whisper.cpp + a model | for transcription | `brew install whisper-cpp` |
| google-genai + `GEMINI_API_KEY` | for AI indexing/music | `pip3 install -r requirements-optional.txt` |
| demucs (pulls PyTorch) | for voice removal | `pip3 install -r requirements-optional.txt` |

## Quick start

```bash
# 1. sanity-check a camera: contact sheet of a clip
python3 scripts/make_sheets.py --cam pov --clip YOUR_CLIP_BASENAME

# 2. catalog a clip (optional, needs whisper / GEMINI_API_KEY)
python3 scripts/transcribe.py --cam pov --clip YOUR_CLIP
python3 scripts/index.py      --cam pov --clip YOUR_CLIP --loc "Mountain pass"
python3 scripts/guardrail.py  --dir ~/trip-reels/output/catalog --apply
python3 scripts/detect.py     --cam pov --clip YOUR_CLIP

# 3. build a reel from a shot list
cp examples/example_reel.py my_reel.py     # edit clip names / times
python3 scripts/build_reel.py my_reel.py --vertical
```

Finished reels land in your configured `output_dir`.

## Layout

| Path | What |
|------|------|
| `config.example.yaml` | documented template; `wizard.py` turns it into `config.yaml` |
| `wizard.py` | interactive configurator |
| `reelkit/` | the library (builder, 360 reframe, catalog, audio, …) |
| `scripts/` | command-line entry points |
| `examples/` | a worked reel script |
| `docs/` | deeper notes: cameras & audio, color grading, event detection |
| `CLAUDE.md` | **the manual for the AI assistant — read this** |

## License

MIT — see [LICENSE](./LICENSE).
