#!/usr/bin/env bash
# One-shot bootstrap for trip-reel-toolkit.
# Safe & idempotent: creates a local venv, installs the light core deps, and on
# macOS installs ffmpeg via Homebrew. It never runs sudo for you — on Linux it
# PRINTS the apt command so you stay in control. Finish by reading the doctor.
set -euo pipefail
cd "$(dirname "$0")"

echo "== trip-reel-toolkit setup =="

# 1) system: ffmpeg
if ! command -v ffmpeg >/dev/null 2>&1; then
  if [[ "$OSTYPE" == darwin* ]] && command -v brew >/dev/null 2>&1; then
    echo "-> installing ffmpeg via Homebrew..."
    brew install ffmpeg
  else
    echo "!! ffmpeg not found. Install it, then re-run this script:"
    echo "     Debian/Ubuntu:  sudo apt install ffmpeg"
    echo "     Fedora:         sudo dnf install ffmpeg"
    echo "     Windows:        winget install Gyan.FFmpeg   (or scoop/choco)"
  fi
else
  echo "-> ffmpeg present."
fi

# 2) python venv + core deps
if [[ ! -d .venv ]]; then
  echo "-> creating virtualenv .venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python3 -m pip install --quiet --upgrade pip
echo "-> installing core Python deps"
python3 -m pip install --quiet -r requirements.txt

echo
echo "Optional features (install when you need them):"
echo "   AI indexing + music:   pip3 install -r requirements-optional.txt   (needs GEMINI_API_KEY)"
echo "   local transcription:   brew install whisper-cpp   (+ a ggml model)"
echo
echo "-> running the doctor:"
python3 scripts/doctor.py || true
echo
echo "Next: python3 wizard.py   (activate the venv first: source .venv/bin/activate)"
