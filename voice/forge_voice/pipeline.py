"""Voice pipeline: listen → STT → LLM/tools → TTS."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from forge_memory.config import ForgeSettings, load_settings

from forge_voice.llm import LLMClient
from forge_voice.stt import STTEngine, build_stt_engine
from forge_voice.transcript import is_meaningful_transcript
from forge_voice.tts import synthesize
from forge_voice.turn import TurnController

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000

_PORTAUDIO_HINT = (
    "PortAudio library not found (required by sounddevice for mic capture). "
    "On Ubuntu/Debian: sudo apt install libportaudio2 portaudio19-dev. "
    "Also install ffmpeg for playback: sudo apt install ffmpeg"
)


def _sounddevice():
    try:
        import sounddevice as sd
    except OSError as exc:
        raise OSError(_PORTAUDIO_HINT) from exc
    return sd


@dataclass
class VoicePipeline:
    settings: ForgeSettings
    stt: STTEngine
    llm: LLMClient
    turns: TurnController = field(default_factory=TurnController)
    mcp_client: Any | None = None
    _playback_stop: threading.Event = field(default_factory=threading.Event)

    async def run_turn(self, audio: np.ndarray) -> str:
        turn_id = self.turns.begin_turn()
        if audio.size == 0:
            logger.info("No speech detected — waiting again.")
            return ""

        transcript = self.stt.transcribe(audio, sample_rate=SAMPLE_RATE)
        if not is_meaningful_transcript(transcript):
            logger.info("Ignored non-speech transcript: %r", transcript)
            return ""
        logger.info("Transcript: %s", transcript)
        return await self._respond(transcript, turn_id=turn_id)

    async def run_text_turn(self, text: str, *, speak: bool = True) -> str:
        """Handle a typed user message (no mic / STT)."""
        turn_id = self.turns.begin_turn()
        if not is_meaningful_transcript(text):
            logger.info("Ignored empty/non-speech input: %r", text)
            return ""
        logger.info("You: %s", text.strip())
        return await self._respond(text.strip(), turn_id=turn_id, speak=speak)

    async def _respond(self, user_text: str, *, turn_id: str, speak: bool = True) -> str:
        if self.mcp_client is not None:
            tools = await self.mcp_client.list_tools()
            reply = await self.llm.chat_with_tools(
                user_text,
                tools=tools,
                tool_caller=self.mcp_client.call_tool,
                turn_cancelled=lambda: self.turns.is_cancelled(turn_id),
            )
        else:
            reply = await self.llm.chat_text(user_text)

        if self.turns.is_cancelled(turn_id):
            logger.info("Turn %s abandoned before reply", turn_id)
            return ""

        print(f"Forge: {reply}", flush=True)
        if speak:
            await self._speak(reply, turn_id=turn_id)
        return reply

    async def _speak(self, text: str, *, turn_id: str) -> None:
        if not text or self.turns.is_cancelled(turn_id):
            return
        audio_bytes, provider = await synthesize(text, self.settings)
        logger.info("TTS via %s (%d bytes)", provider, len(audio_bytes))
        if self.turns.is_cancelled(turn_id):
            return
        self._play_audio(audio_bytes, turn_id=turn_id)

    def _play_audio(self, audio_bytes: bytes, *, turn_id: str) -> None:
        """Play audio via ffplay (handles mp3 from edge-tts and wav from piper)."""
        import os
        import subprocess
        import tempfile

        self._playback_stop.clear()

        def _monitor_barge_in() -> None:
            while not self._playback_stop.is_set():
                if self.turns.is_cancelled(turn_id):
                    self._playback_stop.set()
                    subprocess.run(["pkill", "-f", "ffplay"], check=False)
                    return
                threading.Event().wait(0.05)

        monitor = threading.Thread(target=_monitor_barge_in, daemon=True)
        monitor.start()

        suffix = ".wav" if audio_bytes[:4] == b"RIFF" else ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            path = tmp.name
        try:
            if self._playback_stop.is_set():
                return
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                check=False,
            )
        finally:
            os.unlink(path)

    def barge_in(self) -> None:
        self.turns.cancel_turn()
        self._playback_stop.set()
        try:
            _sounddevice().stop()
        except OSError:
            pass


def record_utterance(
    settings: ForgeSettings,
    *,
    sample_rate: int = SAMPLE_RATE,
    max_seconds: float = 12.0,
    max_wait_for_speech_s: float = 20.0,
) -> np.ndarray:
    """Wait for speech, then record until silence after speech starts."""
    sd = _sounddevice()
    silence_ms = settings.vad_silence_ms
    min_utterance_ms = settings.vad_min_utterance_ms
    block = int(sample_rate * 0.1)  # 100ms
    silence_needed = max(1, int(silence_ms / 100))
    min_speech_blocks = max(1, int(min_utterance_ms / 100))
    max_speech_blocks = int(max_seconds / 0.1)
    max_wait_blocks = int(max_wait_for_speech_s / 0.1)

    frames: list[np.ndarray] = []
    silent_blocks = 0
    speech_started = False
    speech_blocks = 0

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
        # Calibrate ambient noise (~500ms)
        noise_samples: list[float] = []
        for _ in range(5):
            data, _ = stream.read(block)
            chunk = data[:, 0]
            noise_samples.append(float(np.sqrt(np.mean(chunk**2))))
        noise_floor = float(np.median(noise_samples)) if noise_samples else 0.0
        threshold = max(noise_floor * 3.5, 0.015)
        logger.info(
            "Mic ready (noise_floor=%.4f, speech_threshold=%.4f). Speak now…",
            noise_floor,
            threshold,
        )

        for _ in range(max_wait_blocks + max_speech_blocks):
            data, _ = stream.read(block)
            chunk = data[:, 0]
            rms = float(np.sqrt(np.mean(chunk**2)))
            is_loud = rms >= threshold

            if not speech_started:
                if is_loud:
                    speech_started = True
                    frames.append(chunk)
                    speech_blocks = 1
                    silent_blocks = 0
                    logger.info("Speech detected…")
                continue

            frames.append(chunk)
            speech_blocks += 1
            if is_loud:
                silent_blocks = 0
            else:
                silent_blocks += 1

            if speech_blocks >= min_speech_blocks and silent_blocks >= silence_needed:
                logger.info("End of utterance (%.1fs)", speech_blocks * 0.1)
                break
            if speech_blocks >= max_speech_blocks:
                logger.info("Max utterance length reached (%.1fs)", max_seconds)
                break
        else:
            if not speech_started:
                logger.info("No speech heard — try again closer to the mic.")
                return np.array([], dtype=np.float32)

    if not frames:
        return np.array([], dtype=np.float32)
    return np.concatenate(frames)


def build_pipeline(
    settings: ForgeSettings | None = None,
    *,
    config_path: str | None = None,
    overlay_path: str | None = None,
    mcp_client: Any | None = None,
) -> VoicePipeline:
    cfg = settings or load_settings(config_path=config_path, overlay_path=overlay_path)
    return VoicePipeline(
        settings=cfg,
        stt=build_stt_engine(cfg),
        llm=LLMClient(cfg),
        mcp_client=mcp_client,
    )
