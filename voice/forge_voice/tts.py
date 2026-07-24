"""Text-to-speech for Forge."""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from forge_memory.config import ForgeSettings

logger = logging.getLogger(__name__)


class TTSProviderError(RuntimeError):
    pass


async def synthesize_edge(text: str, *, voice: str, timeout_s: int = 10) -> bytes:
    communicate = edge_tts.Communicate(text, voice=voice)
    chunks: list[bytes] = []

    async def _collect() -> None:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

    await asyncio.wait_for(_collect(), timeout=timeout_s)
    if not chunks:
        raise TTSProviderError("edge-tts returned no audio")
    return b"".join(chunks)


def synthesize_piper(text: str, *, model_path: Path, piper_bin: str = "piper") -> bytes:
    if not model_path.is_file():
        raise TTSProviderError(f"Piper model not found: {model_path}")
    bin_path = shutil.which(piper_bin) or piper_bin
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [bin_path, "--model", str(model_path), "--output_file", str(out_path)],
            input=text,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise TTSProviderError(proc.stderr.strip() or "piper failed")
        return out_path.read_bytes()
    finally:
        out_path.unlink(missing_ok=True)


async def synthesize(
    text: str,
    settings: ForgeSettings,
    *,
    force_provider: str | None = None,
) -> tuple[bytes, str]:
    """Return (audio_bytes, provider_used)."""
    provider = force_provider or settings.tts_provider
    if settings.offline:
        provider = "piper"

    if provider == "edge":
        audio = await synthesize_edge(
            text,
            voice=settings.edge_tts_voice,
            timeout_s=settings.tts_speak_timeout_s,
        )
        return audio, "edge"

    if provider == "piper":
        audio = synthesize_piper(
            text,
            model_path=settings.piper_model,
            piper_bin=settings.piper_bin,
        )
        return audio, "piper"

    if provider == "auto":
        try:
            audio = await synthesize_edge(
                text,
                voice=settings.edge_tts_voice,
                timeout_s=settings.tts_speak_timeout_s,
            )
            return audio, "edge"
        except (TimeoutError, TTSProviderError, OSError) as exc:
            logger.warning("edge-tts failed (%s), falling back to piper", exc)
            audio = synthesize_piper(
                text,
                model_path=settings.piper_model,
                piper_bin=settings.piper_bin,
            )
            return audio, "piper"

    raise TTSProviderError(f"Unknown TTS provider: {provider}")
