#!/usr/bin/env bash
# Pre-demo health check + printable script steps.
set -euo pipefail
cd "$(dirname "$0")/.."

ok() { printf '  [ok] %s\n' "$*"; }
warn() { printf '  [!!] %s\n' "$*"; }
fail=0

echo "== forge-os demo checklist =="
echo

echo "-- Environment --"
if [[ -f .env ]] && grep -qE '^GROQ_API_KEY=.+' .env; then
  ok "GROQ_API_KEY present in .env"
else
  warn "GROQ_API_KEY missing — copy .env.example and set the key"
  fail=1
fi

echo
echo "-- Packages --"
if uv run forge-mcp --list-tools >/tmp/forge-tools.txt 2>/dev/null; then
  count=$(wc -l </tmp/forge-tools.txt)
  ok "forge-mcp --list-tools ($count tools)"
  if ! grep -q web_search /tmp/forge-tools.txt; then
    warn "web_search not listed"
    fail=1
  fi
else
  warn "forge-mcp --list-tools failed (run: uv sync)"
  fail=1
fi

echo
echo "-- System audio --"
if ldconfig -p 2>/dev/null | grep -q libportaudio; then
  ok "PortAudio library present"
else
  warn "PortAudio missing — mic mode needs: sudo apt install libportaudio2 portaudio19-dev"
fi
if command -v ffplay >/dev/null 2>&1; then
  ok "ffplay available"
else
  warn "ffplay missing — TTS playback needs: sudo apt install ffmpeg"
fi

echo
echo "-- Playwright (demo item 6) --"
if uv run playwright --version >/dev/null 2>&1; then
  ok "playwright CLI available"
  if uv run python -c "from playwright.sync_api import sync_playwright; sync_playwright().start().chromium.launch(headless=True).close()" 2>/dev/null; then
    ok "Chromium launches"
  else
    warn "Chromium not installed — run: uv run playwright install chromium"
  fi
else
  warn "playwright not on PATH via uv — run: uv sync && uv run playwright install chromium"
fi

echo
echo "-- Piper (optional TTS fallback) --"
if [[ -f data/piper/en_US-lessac-medium.onnx ]]; then
  ok "Piper model found"
else
  warn "Piper model absent (optional) — see docs/runbook.md"
fi

echo
echo "-- Unit tests (quick) --"
if uv run pytest -q --tb=no >/tmp/forge-pytest.txt 2>&1; then
  ok "pytest green ($(tail -1 /tmp/forge-pytest.txt))"
else
  warn "pytest failed — see /tmp/forge-pytest.txt"
  fail=1
fi

echo
echo "== Live demo steps =="
cat <<'EOF'
  1. Time          → “Forge, what time is it?”
  2. News          → “What’s the top tech news today?”
  3. Remember      → “Remember that my holiday project is called forge-os.”
  4. Recall        → “What holiday project am I working on?”
  5. Search        → “Search for Pipecat voice agents and give me one useful fact.”
  6. Browser       → “Open https://example.com and tell me the page title.”
  7. Interrupt     → Start news, then talk over the reply (TTS stops).

  Terminals:
    A: uv run forge-mcp --transport sse
    B: uv run forge-voice --config configs/cpu.yaml
       (or --text / --text --no-speak)

  Full copy: docs/demo-script.md
EOF

echo
if [[ "$fail" -ne 0 ]]; then
  echo "Checklist finished with warnings — fix [!!] items before audience."
  exit 1
fi
echo "Checklist OK — ready to demo."
