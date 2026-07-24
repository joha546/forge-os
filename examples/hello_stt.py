#!/usr/bin/env python3
"""One-shot mic capture + Whisper transcript."""

import numpy as np
from forge_memory.config import load_settings
from forge_voice.pipeline import record_utterance
from forge_voice.stt import build_stt_engine


def main() -> None:
    settings = load_settings(overlay_path="configs/cpu.yaml")
    print("Speak now…")
    audio = record_utterance(settings)
    if audio.size == 0:
        print("No audio captured.")
        return
    engine = build_stt_engine(settings)
    text = engine.transcribe(np.asarray(audio, dtype=np.float32))
    print(f"Transcript: {text}")


if __name__ == "__main__":
    main()
