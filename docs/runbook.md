# Runbook

Ops notes for Linux demos. Spec: [SPEC.md](../SPEC.md). Contracts: [contracts.md](contracts.md).

## Two processes

| Process | Command | Default |
|---------|---------|---------|
| MCP tools | `uv run forge-mcp --transport sse` | `http://127.0.0.1:8765/sse` |
| Voice | `uv run forge-voice --config configs/cpu.yaml` | Mic loop |
| Voice text | `… --text` | Type instead of mic |
| Voice no tools | `… --no-mcp` | Phase 0 chitchat |

List tools without starting SSE: `uv run forge-mcp --list-tools`.

## Environment

- Copy `.env.example` → `.env`; set `GROQ_API_KEY`.
- `load_settings` loads repo-root `.env` automatically; exported env still wins.
- Never commit `.env`.

## Audio

```bash
sudo apt install libportaudio2 portaudio19-dev ffmpeg
arecord -l          # list capture devices
ffplay -version     # needed for TTS playback
```

If PortAudio is missing, `forge-voice` (mic mode) fails with an install hint. Use `--text` meanwhile.

## Playwright

```bash
uv run playwright install chromium
uv run python examples/hello_browser.py
```

Allowlist defaults: `example.com`, `*.wikipedia.org`. Override with `BROWSER_ALLOWLIST` or `BROWSER_ALLOW_ALL=1` (never default to allow-all in demos).

## Piper TTS fallback

1. Download `en_US-lessac-medium.onnx` (+ matching `.json`) into `data/piper/`.
2. Install `piper` CLI on `PATH`, or set `PIPER_BIN`.
3. Force: `TTS_PROVIDER=piper` or `FORGE_OFFLINE=1`.

## Search

Default backend is DuckDuckGo via the `ddgs` package. Empty results used to happen with the old `duckduckgo-search` package — keep `ddgs` installed (`uv sync`).

## Memory paths

Under `FORGE_DATA_DIR` (default `./data`):

- `data/sqlite/forge.db`
- `data/chroma/`

Safe to delete between demos if you want a clean memory slate.

## Common failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| 401 from Groq | Missing/invalid key | Fix `.env` / restart voice |
| `tool_use_failed` | Llama XML tool format | Voice recovers by parsing `failed_generation` |
| Search returns nothing | Old DDG package / network | `uv sync`; check outbound HTTPS |
| Browser `ALLOWLIST_DENIED` | Host not listed | Use example.com or update allowlist |
| Browser backend error | Chromium not installed | `uv run playwright install chromium` |
| MCP connect fail | Server not running | Start `forge-mcp` first; voice falls back to no-tools |
| `. . . .` transcripts | Noise / VAD | Speak closer; text mode for demos |

## Health check

```bash
bash scripts/demo_checklist.sh
```
