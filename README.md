# forge-os

Local-first FRIDAY/JARVIS-style voice assistant — **Forge**. Free/self-hosted stack only.

## Docs

- [SPEC.md](SPEC.md) — vision, phases, demo script
- [docs/contracts.md](docs/contracts.md) — env, MCP tools, memory schemas
- [docs/session-context.md](docs/session-context.md) — agent session pack
- [docs/demo-script.md](docs/demo-script.md) — printable live demo steps
- [docs/runbook.md](docs/runbook.md) — troubleshooting / ops
- [tasks/todo.md](tasks/todo.md) — implementation tasks

## Prerequisites (Linux)

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- **PortAudio** (mic capture via `sounddevice`): `sudo apt install libportaudio2 portaudio19-dev`
- `ffmpeg` / `ffplay` (audio playback): `sudo apt install ffmpeg`
- Free [Groq API key](https://console.groq.com)
- Mic + speakers

## Quickstart

```bash
git clone <repo> forge-os && cd forge-os
cp .env.example .env   # set GROQ_API_KEY=gsk_...
bash scripts/bootstrap.sh
```

`.env` in the repo root is loaded automatically at runtime (`load_settings`). Exporting vars still overrides `.env`.

### Phase 0 — voice only (no MCP)

```bash
uv run python examples/hello_tts.py
uv run python examples/hello_stt.py    # speak once
uv run python examples/hello_llm.py "What is forge-os?"

# Mic mode (needs PortAudio + working mic)
uv run forge-voice --config configs/cpu.yaml --no-mcp

# Text mode — no mic; type questions, hear + see replies
uv run forge-voice --config configs/cpu.yaml --no-mcp --text

# Text only (no speakers / skip ffplay)
uv run forge-voice --config configs/cpu.yaml --no-mcp --text --no-speak
```

### Phase 1+ — tools (two terminals)

```bash
# Terminal A
uv run forge-mcp --transport sse --host 127.0.0.1 --port 8765

# Terminal B
uv run forge-voice --config configs/cpu.yaml
# or: uv run forge-voice --config configs/cpu.yaml --text
```

### Phase 2 — browser (once)

```bash
uv run playwright install chromium
uv run python examples/hello_browser.py   # expect title Example Domain
```

### Pre-demo checklist

```bash
bash scripts/demo_checklist.sh
```

## Config

- `configs/default.yaml` — base settings
- `configs/cpu.yaml` — CPU laptop overlay (default demo)
- `configs/gpu.yaml` — CUDA Whisper overlay

Env overrides yaml — see `.env.example` and `docs/contracts.md`.

## Test

```bash
uv run pytest
uv run ruff check .
```

## Demo script

See [docs/demo-script.md](docs/demo-script.md) (also SPEC.md § Demo script) — time, news, memory, search, browser, interrupt.

## License

MIT
