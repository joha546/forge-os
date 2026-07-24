# Tasks: forge-os

Ordered Phase 0 → 2 for holiday MVP. Phase 3+ is backlog only (includes wake word, offline LLM, SIP, C-suite).  
See [plan.md](plan.md) for dependency graph and vertical-slice rationale. Spec: [SPEC.md](../SPEC.md).

**Human-blocked (Phases 0–2): none.**

---

## Phase 0 — Skeleton + hello voice loop (no tools)

### T0.1 — uv workspace + configs

- **Goal:** Scaffold monorepo so later slices have packages/configs; `uv sync` works.
- **Files:** `pyproject.toml`, `voice/pyproject.toml`, `mcp_server/pyproject.toml`, `memory/pyproject.toml`, package `__init__.py` stubs, `configs/{default,cpu,gpu}.yaml`, `.env.example`, `data/.gitkeep`, `.gitignore` updates
- **Acceptance:**
  - [x] uv workspace members: `voice`, `mcp_server`, `memory`
  - [x] Configs encode SPEC defaults (LLM, Whisper `base`/cpu, GuyNeural, MCP SSE URL)
  - [x] `.env.example` lists `GROQ_API_KEY` and other SPEC §7.1 vars
- **Verify:** `uv sync` exits 0
- **Deps:** None (PR1)
- **Scope:** M

### T0.2 — Hello TTS (edge-tts)

- **Goal:** Speak a fixed string via edge-tts `en-US-GuyNeural`.
- **Files:** `voice/forge_voice/tts.py`, `examples/hello_tts.py`, deps in `voice/pyproject.toml`
- **Acceptance:**
  - [x] `synthesize(text)` returns playable audio
  - [x] Voice configurable via `EDGE_TTS_VOICE` / config
- **Verify:** `uv run python examples/hello_tts.py` — hear speech
- **Deps:** T0.1
- **Scope:** S

### T0.3 — Hello STT (faster-whisper)

- **Goal:** Capture one mic utterance → transcript (`base`/cpu).
- **Files:** `voice/forge_voice/stt.py`, `examples/hello_stt.py`
- **Acceptance:**
  - [x] Whisper model/device/compute_type from config/env
  - [ ] Prints non-empty transcript for a clear English phrase (manual mic)
- **Verify:** `uv run python examples/hello_stt.py` — manual speak once
- **Deps:** T0.1
- **Scope:** S

### T0.4 — Hello LLM (Groq, no tools)

- **Goal:** OpenAI-compatible Groq client + Forge persona; text in → text out.
- **Files:** `voice/forge_voice/llm.py`, `voice/forge_voice/persona.py`, `examples/hello_llm.py` (or CLI flag)
- **Acceptance:**
  - [x] Uses `GROQ_API_KEY`, model `llama-3.3-70b-versatile`
  - [x] System prompt identifies assistant as Forge
  - [x] No tool calling yet (text path); tool loop in `chat_with_tools`
- **Verify:** `uv run python examples/hello_llm.py` (or equiv.) with a one-line prompt — sensible reply
- **Deps:** T0.1
- **Scope:** S

### T0.5 — Spoken Q&A loop (mic → STT → LLM → TTS)

- **Goal:** Phase 0 exit path: interruptible-ready voice conversation without MCP.
- **Files:** `voice/forge_voice/pipeline.py`, `voice/forge_voice/main.py`, Pipecat (or minimal) wiring
- **Acceptance:**
  - [x] Listen → VAD end → transcribe → Groq → speak
  - [x] Entry point `uv run forge-voice` works with `configs/cpu.yaml`
  - [x] No MCP dependency (`--no-mcp`)
- **Verify:** Manual — ask a short question; hear spoken answer
- **Deps:** T0.2, T0.3, T0.4
- **Scope:** M

### T0.6 — Barge-in (cancel TTS; abandon in-flight work)

- **Goal:** User speech during playback stops TTS and starts a new turn; tool-abandon hook ready for Phase 1.
- **Files:** `voice/forge_voice/pipeline.py` (cancel token / turn id), optional small helper module
- **Acceptance:**
  - [x] In-flight turn marked abandoned; late results ignored (`TurnController`)
  - [x] Stub/API exists to cancel pending tool calls (`turn_cancelled` in tool loop)
  - [ ] Talking over Forge stops playback promptly (manual)
- **Verify:** Manual — start a long answer, interrupt mid-sentence; new utterance handled
- **Deps:** T0.5
- **Scope:** S

### T0.7 — README Phase 0 quickstart

- **Goal:** Stranger can run hello loop on Linux in ≤15 minutes (excl. model downloads).
- **Files:** `README.md`, optionally `docs/runbook.md` stub
- **Acceptance:**
  - [x] Prerequisites, `.env`, `uv sync`, `forge-voice` commands documented
  - [x] Points to SPEC + demo script
  - [x] CPU vs GPU config called out
- **Verify:** Manual read-through / dry-run of commands
- **Deps:** T0.6
- **Scope:** S

### Checkpoint A (Phase 0 exit)

- [x] Spoken Q&A path implemented (`forge-voice` / `--text` / `--no-mcp`)
- [x] Barge-in API implemented (`TurnController` + TTS cancel)
- [ ] Human mic/barge-in rehearsal before claiming a live audience demo

---

## Phase 1 — MCP tools wired (vertical slices)

### T1.1 — MCP + `system_time` end-to-end

- **Goal:** First tool vertical: FastMCP SSE (+ stdio debug) + `system_time` + voice dynamic tool loop.
- **Files:** `mcp_server/forge_mcp/server.py`, `mcp_server/forge_mcp/tools/system.py`, `voice/forge_voice/mcp_client.py`, `voice/forge_voice/llm.py` (tool loop), `mcp_server/tests/test_system_time.py`
- **Acceptance:**
  - [x] `uv run forge-mcp --list-tools` lists all tools
  - [x] Voice loads schemas via MCP `list_tools` (not hardcoded duplicate list)
  - [ ] “What time is it?” invokes `system_time` and speaks result (manual E2E)
- **Verify:** Two terminals; manual time question; `uv run pytest mcp_server/tests/test_system_time.py`
- **Deps:** Checkpoint A
- **Scope:** M

### T1.2 — Memory store / recall (SQLite + Chroma)

- **Goal:** Persist facts across restarts; semantic recall.
- **Files:** `memory/forge_memory/*`, `mcp_server/forge_mcp/tools/memory_tools.py`, `memory/tests/*`, `mcp_server/tests/test_memory_tools.py`
- **Acceptance:**
  - [x] `memory_store` / `memory_recall` / `memory_list_recent` match contracts
  - [x] Data under `FORGE_DATA_DIR`; survives MCP restart (unit tested)
  - [x] Unit tests for store → recall
- **Verify:** `uv run pytest memory/tests mcp_server/tests/test_memory_tools.py`; manual remember/recall
- **Deps:** T1.1
- **Scope:** M

### T1.3 — News (`get_news`)

- **Goal:** RSS tech/world/science feeds → spoken summary path.
- **Files:** `mcp_server/forge_mcp/tools/news.py`, `mcp_server/forge_mcp/adapters/*`, `configs/default.yaml` feeds, `mcp_server/tests/test_news.py` (fixtures/mocks)
- **Acceptance:**
  - [x] `get_news` returns `{ok, items[]}` per SPEC
  - [x] Network mocked in unit tests
- **Verify:** `uv run pytest mcp_server/tests/test_news.py`; manual “top tech news”
- **Deps:** T1.2
- **Scope:** S

### T1.4 — Web search (`web_search`)

- **Goal:** DuckDuckGo search tool for demo factoid.
- **Files:** `mcp_server/forge_mcp/tools/search.py`, adapter, `mcp_server/tests/test_search.py` (mocked)
- **Acceptance:**
  - [x] `web_search` returns `{ok, backend, results[]}`
  - [x] `SEARCH_BACKEND=ddg` default; SearXNG hook optional/stub only
- **Verify:** `uv run pytest mcp_server/tests/test_search.py`; manual Pipecat search question
- **Deps:** T1.3
- **Scope:** S

### T1.5 — Notes (`notes_add` / `notes_list`)

- **Goal:** Structured notes distinct from semantic memory.
- **Files:** `mcp_server/forge_mcp/tools/system.py` or `notes.py`, SQLite notes table usage, tests
- **Acceptance:**
  - [x] Add + list notes per contracts
  - [x] Tests cover happy path + error shape `{ok:false}` (validation via memory_store empty text)
- **Verify:** `uv run pytest` relevant tests; manual add/list via voice or MCP CLI
- **Deps:** T1.4
- **Scope:** S

### T1.6 — Demo script items 1–5

- **Goal:** Phase 1 exit gate on real mic + Groq.
- **Files:** none required (maybe `docs/demo-script.md` copy); fix bugs found
- **Acceptance:**
  - [x] Printable demo copy + checklist exist (`docs/demo-script.md`, `scripts/demo_checklist.sh`)
  - [ ] SPEC demo lines 1–5 succeed on `configs/cpu.yaml` (manual)
  - [x] Tools still dynamic from MCP
- **Verify:** `bash scripts/demo_checklist.sh`; manual demo script § SPEC “Demo script”
- **Deps:** T1.5
- **Scope:** S

### Checkpoint B (Phase 1 exit)

- [x] pytest green for memory/tools
- [ ] Demo 1–5 pass (manual — run `bash scripts/demo_checklist.sh` then live script)
- [ ] Human review before Phase 2

---

## Phase 2 — Playwright + TTS/LLM polish

### T2.1 — Groq model fallback on 429

- **Goal:** Auto-switch `llama-3.3-70b-versatile` → `openai/gpt-oss-20b` → `llama-3.1-8b-instant`.
- **Files:** `voice/forge_voice/llm.py`, `voice/tests/test_llm_fallback.py`
- **Acceptance:**
  - [x] On 429/rate-limit: next fallback model (mocked test)
  - [x] Clear log: switching LLM to …
- **Verify:** `uv run pytest voice/tests/test_llm_fallback.py` (mocked HTTP)
- **Deps:** Checkpoint B
- **Scope:** S

### T2.2 — Piper TTS fallback + bootstrap

- **Goal:** edge failure / `FORGE_OFFLINE=1` / `TTS_PROVIDER=piper` → Piper speaks.
- **Files:** `voice/forge_voice/tts.py`, `scripts/bootstrap.sh`, Piper paths under `data/piper/`, tests for provider selection
- **Acceptance:**
  - [x] Fallback triggers per SPEC §4 TTS rules (unit tested)
  - [x] Bootstrap documents Piper path (`scripts/bootstrap.sh`)
- **Verify:** Force edge fail or `FORGE_OFFLINE=1`; hear Piper; unit test provider selection
- **Deps:** Checkpoint B
- **Scope:** M

### T2.3 — Playwright browser tools + allowlist

- **Goal:** `browser_navigate` / `browser_get_text` / `browser_snapshot` for allowlisted hosts.
- **Files:** `mcp_server/forge_mcp/tools/browser.py`, allowlist helper, tests, README playwright install note
- **Acceptance:**
  - [x] example.com title retrievable (`examples/hello_browser.py` + optional live pytest)
  - [x] Non-allowlisted URL returns `{ok:false}` (`ALLOWLIST_DENIED`)
  - [x] Headless default
- **Verify:** `uv run playwright install chromium` once; `uv run python examples/hello_browser.py`; pytest
- **Deps:** Checkpoint B
- **Scope:** M

### T2.4 — Demo items 6–7 + interrupt rehearsal

- **Goal:** Holiday MVP showcase gate.
- **Files:** bugfixes only as needed; `docs/demo-script.md`, `scripts/demo_checklist.sh`
- **Acceptance:**
  - [x] Browser smoke path ready (`examples/hello_browser.py`)
  - [ ] Demo line 6 (browser title) works via voice/text (manual)
  - [ ] Demo line 7: interrupt during news/TTS abandons tools + cancels speech (manual)
  - [ ] Piper and LLM fallback rehearsed once (manual)
- **Verify:** Full SPEC demo script on CPU laptop; `bash scripts/demo_checklist.sh`
- **Deps:** T2.1, T2.2, T2.3
- **Scope:** S

### Checkpoint C — Holiday MVP done

- [ ] Demo 1–7 pass (or 1–5 + 6–7) — manual
- [x] No Phase 3+ work started unless human explicitly prioritizes

---

## Phase 3+ backlog (post-MVP — do not start before Checkpoint C)

Smaller leftovers from original Phase 3 niceties, then user-requested roadmap epics.

### Smaller niceties

- [ ] **T3.N1** — SearXNG adapter behind `SEARCH_BACKEND=searxng`
- [ ] **T3.N2** — Memory improvements (chunking, auto-index turns)
- [ ] **T3.N3** — CLI/TUI status (mic level, last tool, model)
- [ ] **T3.N4** — FAISS alternative behind same `VectorStore` protocol

### Phase 3 — Always-on wake word

- [ ] **T3.1** — Spike openWakeWord on Linux mic; measure CPU idle cost
- [ ] **T3.2** — “Hey Forge” gate before STT; keep push-to-talk / open-mic mode as fallback
- [ ] **T3.3** — Background daemon mode docs (systemd user unit optional)
- **Acceptance (phase):** Forge idle-listens and only runs full STT→LLM after wake phrase
- **Verify:** Leave running 10+ min; wake works; no continuous Groq calls while silent

### Phase 4 — Zero-cloud offline LLM

- [ ] **T4.1** — Abstract LLM provider interface (Groq vs local)
- [ ] **T4.2** — Ollama (or equiv.) adapter; pick default local model good enough for tools
- [ ] **T4.3** — Auto-select: online→Groq, `FORGE_OFFLINE=1` or Groq unreachable→local
- **Acceptance (phase):** Full tool loop works with no Groq key when local model running
- **Verify:** Disconnect network / unset key; ask time + memory with local LLM
- **Note:** Groq remains **default** when online (MVP behavior unchanged)

### Phase 5 — Phone calling / SIP

- [ ] **T5.1** — Spike free SIP stack (Asterisk or FreeSWITCH) + softphone on LAN
- [ ] **T5.2** — Bridge SIP audio ↔ Forge STT/TTS pipeline
- [ ] **T5.3** — Dial-out / answer tool(s) via MCP with explicit confirmations
- **Acceptance (phase):** Place or receive one LAN SIP call and converse with Forge
- **Verify:** Manual softphone call; no paid telephony API
- **Ask first:** Any cloud SIP trunk (even free-tier) before adding

### Phase 6 — Multi-agent C-suite dashboards

- [ ] **T6.1** — Define agent roles (e.g. research / memory / browser) as MCP-backed workers — not a product clone
- [ ] **T6.2** — Local web dashboard: status, last turns, tool activity
- [ ] **T6.3** — Voice can delegate “have research dig into X” to a worker; results return to Forge
- **Acceptance (phase):** One delegated multi-agent task visible on localhost dashboard
- **Verify:** Manual demo; still free/self-hosted; no mobile app requirement

---

## Task index

| ID | Phase | Goal (short) |
|----|-------|--------------|
| T0.1 | 0 | Workspace + configs |
| T0.2 | 0 | Hello TTS |
| T0.3 | 0 | Hello STT |
| T0.4 | 0 | Hello LLM |
| T0.5 | 0 | Spoken Q&A loop |
| T0.6 | 0 | Barge-in |
| T0.7 | 0 | README |
| T1.1 | 1 | MCP + system_time E2E |
| T1.2 | 1 | Memory |
| T1.3 | 1 | News |
| T1.4 | 1 | Search |
| T1.5 | 1 | Notes |
| T1.6 | 1 | Demo 1–5 |
| T2.1 | 2 | LLM fallback |
| T2.2 | 2 | Piper |
| T2.3 | 2 | Playwright |
| T2.4 | 2 | Demo 6–7 |
| T3.* | 3+ | Wake word + niceties |
| T4.* | 4 | Offline LLM |
| T5.* | 5 | SIP |
| T6.* | 6 | C-suite dashboards |
