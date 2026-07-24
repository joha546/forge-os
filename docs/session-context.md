# Session context: forge-os

Read this first every coding session. Then open only the files needed for the **current task**.

## Goal & persona

**forge-os** — local-first FRIDAY/JARVIS-style voice assistant for demos and personal use.  
**Persona:** **Forge** — concise, competent, slightly dry wit; confirms tool actions briefly.

Speak → local STT → Groq (free) reasons + tools → speak back. Tools live on a local MCP server.

## Hard constraints

- **Free / self-hosted only** — no paid STT, TTS, LLM, browser, or telephony APIs. Groq **free tier** is the only cloud LLM for MVP.
- **Linux-first** — macOS best-effort docs; Windows unsupported for MVP.
- **Two processes** — (A) `forge-mcp` tools + memory, (B) `forge-voice` mic/STT/LLM/TTS.
- **CPU-first defaults** — Whisper `base` / cpu; GPU optional via config.
- **Contracts win** — if unsure about env, tools, or JSON shapes, follow `docs/contracts.md` (`CONTRACT_VERSION = 1` for MVP).

## Canonical docs (load selectively)

| Doc | When to load |
|-----|----------------|
| [`SPEC.md`](../SPEC.md) | Vision, phases, demo script, boundaries |
| [`docs/contracts.md`](contracts.md) | Env, MCP schemas, memory, voice↔MCP, Phase 3–6 reserved |
| [`tasks/todo.md`](../tasks/todo.md) | Ordered work; acceptance + verify |
| [`tasks/plan.md`](../tasks/plan.md) | Dependency graph / vertical slices |

Do **not** paste the entire SPEC into context. Load the section for the active task only.

## Current phase rule

1. Open `tasks/todo.md`.
2. Find the **first unchecked** task (`T0.1` → … → `T2.4`).
3. Work **only that task** (and its listed files).
4. Do **not** start Phase 3–6 (wake word, offline LLM, SIP, C-suite) until Checkpoint C (Phase 2 demo) is done — unless the human explicitly prioritizes a backlog item.
5. After finishing: mark the task done, run its **Verify** step, stop or take the next unchecked task.

## Boundaries (from SPEC)

- **Always:** free/self-hosted stack; run relevant tests before claiming a phase/slice done; update SPEC/contracts when decisions change; env overrides yaml.
- **Ask first:** paid providers; license changes; new long-running infra (Docker beyond optional SearXNG); making `BROWSER_ALLOW_ALL=1` the default; breaking MCP/tool renames.
- **Never:** commit `.env` / secrets; delete failing tests to go green; silently swap Groq for a paid LLM; invent tool JSON that contradicts `docs/contracts.md`.

## Definition of done (one slice / task)

A task is done only when **all** are true:

- [ ] Acceptance criteria in `tasks/todo.md` for that task ID are met  
- [ ] **Verify** command or manual check from the task passes  
- [ ] Changes match `docs/contracts.md` (no silent schema drift)  
- [ ] No secrets in the diff  
- [ ] Scope stayed within the task’s file list (± small bugfixes required to verify)  
- [ ] If behavior/decisions changed: SPEC and/or contracts updated in the same change  

## Stack reminders (MVP)

- LLM: Groq `llama-3.3-70b-versatile` → fallbacks `openai/gpt-oss-20b` → `llama-3.1-8b-instant`  
- STT: faster-whisper · TTS: edge-tts `en-US-GuyNeural` (`auto` → Piper)  
- MCP: SSE default · Memory: SQLite + Chroma · Search: DuckDuckGo  

## Confusion

If SPEC, contracts, and code disagree: **stop**, cite both sides, ask the human. Do not guess.
