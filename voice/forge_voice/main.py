"""CLI entry for forge-voice."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import numpy as np
from forge_memory.config import load_settings

from forge_voice.mcp_client import open_mcp_client
from forge_voice.pipeline import SAMPLE_RATE, build_pipeline, record_utterance

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("forge-voice")


async def _run_text_loop(pipeline, *, speak: bool) -> None:
    logger.info("Text mode ready. Type a question and press Enter (empty / Ctrl+C to quit).")
    while True:
        try:
            line = await asyncio.to_thread(input, "You> ")
        except EOFError:
            break
        if not line.strip():
            logger.info("Empty line — quitting text mode.")
            break
        try:
            await pipeline.run_text_turn(line, speak=speak)
        except Exception as exc:
            logger.exception("Turn failed: %s", exc)
            print(f"Forge: Sorry — that turn failed ({exc}). Try again.", flush=True)


async def _run_voice_loop(pipeline, settings) -> None:
    logger.info("Warming up Whisper (%s/%s)…", settings.whisper_model, settings.whisper_device)
    pipeline.stt.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32))
    logger.info(
        "Forge ready (STT %s/%s, TTS %s). Waiting for you to speak…",
        settings.whisper_model,
        settings.whisper_device,
        settings.tts_provider,
    )
    while True:
        logger.info("Listening… (speak, then pause; Ctrl+C to quit)")
        audio = await asyncio.to_thread(record_utterance, settings)
        if audio.size == 0:
            continue
        try:
            await pipeline.run_turn(audio)
        except Exception as exc:
            logger.exception("Turn failed: %s", exc)


async def _run_agent(args: argparse.Namespace, settings, mcp_client) -> None:
    pipeline = build_pipeline(settings, mcp_client=mcp_client)
    speak = not args.no_speak
    if args.text:
        await _run_text_loop(pipeline, speak=speak)
    else:
        await _run_voice_loop(pipeline, settings)


async def _async_main(args: argparse.Namespace) -> int:
    settings = load_settings(
        config_path="configs/default.yaml",
        overlay_path=args.config,
    )
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY missing. Set it in .env (repo root) or export it.")
        return 1

    try:
        if args.no_mcp:
            await _run_agent(args, settings, mcp_client=None)
            return 0

        mcp_ready = False
        try:
            async with open_mcp_client(settings.mcp_url) as mcp_client:
                mcp_ready = True
                logger.info("MCP connected: %s", settings.mcp_url)
                await _run_agent(args, settings, mcp_client)
        except Exception as exc:
            if not mcp_ready:
                logger.warning(
                    "MCP unavailable (%s); continuing without tools. "
                    "Start forge-mcp or pass --no-mcp.",
                    exc,
                )
                await _run_agent(args, settings, mcp_client=None)
            else:
                logger.exception("Session error: %s", exc)
                return 1
    except KeyboardInterrupt:
        logger.info("Goodbye.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Forge voice assistant")
    parser.add_argument(
        "--config",
        default="configs/cpu.yaml",
        help="Config overlay path (merged onto default.yaml)",
    )
    parser.add_argument("--no-mcp", action="store_true", help="Phase 0 mode: no MCP tools")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Type questions in the terminal (no mic); print + speak replies",
    )
    parser.add_argument(
        "--no-speak",
        action="store_true",
        help="Print replies only (skip TTS / ffplay)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_async_main(args)))
