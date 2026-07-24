# Demo script (one page)

Printable copy of SPEC § Demo script. Use with `bash scripts/demo_checklist.sh` before an audience.

## Setup (5 min before)

1. Headset mic plugged in.
2. Terminal A: `uv run forge-mcp --transport sse`
3. Terminal B: `uv run forge-voice --config configs/cpu.yaml`  
   (or `--text` if the mic is unavailable)
4. Confirm logs mention MCP connected and TTS ready.
5. Throwaway: “Forge, what time is it?”

## Live script

| # | You say | Expected |
|---|---------|----------|
| 1 | “Forge, what time is it?” | Speaks local time via `system_time`. |
| 2 | “What’s the top tech news today?” | Calls `get_news`; summarizes 2–3 headlines aloud. |
| 3 | “Remember that my holiday project is called forge-os.” | `memory_store`; brief confirmation. |
| 4 | “What holiday project am I working on?” | `memory_recall` → “forge-os”. |
| 5 | “Search for Pipecat voice agents and give me one useful fact.” | `web_search` → one crisp fact. |
| 6 | *(Phase 2)* “Open https://example.com and tell me the page title.” | Playwright → “Example Domain”. |
| 7 | *(Interrupt)* Start asking news, then talk over the reply | TTS stops; new turn begins. |

## Contingencies

- **Groq 429:** Forge should log `switching LLM to …` and continue, or ask to retry in a minute. Rehearse once.
- **edge-tts fail / `FORGE_OFFLINE=1`:** Piper continues the demo if the model is under `data/piper/`.
- **No mic:** use `--text` / `--text --no-speak` for the same tool path.

## Browser one-shot (no voice)

```bash
uv run playwright install chromium   # once
uv run python examples/hello_browser.py
```
