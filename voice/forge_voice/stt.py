"""Speech-to-text for Forge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from faster_whisper import WhisperModel
from forge_memory.config import ForgeSettings


class STTEngine(Protocol):
    def transcribe(self, audio: np.ndarray, *, sample_rate: int = 16000) -> str: ...


@dataclass
class FasterWhisperEngine:
    model_size: str
    device: str
    compute_type: str
    _model: WhisperModel | None = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(self, audio: np.ndarray, *, sample_rate: int = 16000) -> str:
        if audio.size == 0:
            return ""
        model = self._get_model()
        segments, _ = model.transcribe(audio, language="en")
        return " ".join(segment.text.strip() for segment in segments).strip()


def build_stt_engine(settings: ForgeSettings) -> FasterWhisperEngine:
    return FasterWhisperEngine(
        model_size=settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
