#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Python packages"
uv sync --all-packages
mkdir -p data/piper data/sqlite data/chroma

echo "==> System audio deps (Ubuntu/Debian)"
if command -v apt-get >/dev/null 2>&1; then
  if ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
    echo "PortAudio missing. Install with:"
    echo "  sudo apt install libportaudio2 portaudio19-dev ffmpeg"
  else
    echo "PortAudio found."
  fi
  if ! command -v ffplay >/dev/null 2>&1; then
    echo "ffplay missing. Install with: sudo apt install ffmpeg"
  fi
fi

echo "Bootstrap complete."
echo "Pre-demo: bash scripts/demo_checklist.sh"
echo "Optional: uv run playwright install chromium"
echo "Optional Piper voice: download en_US-lessac-medium.onnx to data/piper/"
