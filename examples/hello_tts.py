#!/usr/bin/env python3
"""Speak a sample line via edge-tts."""

import asyncio
import sys

from forge_memory.config import load_settings
from forge_voice.tts import synthesize


async def main() -> None:
    settings = load_settings()
    text = sys.argv[1] if len(sys.argv) > 1 else "Hello, I am Forge."
    audio, provider = await synthesize(text, settings, force_provider="edge")
    out = "hello_tts.mp3"
    with open(out, "wb") as fh:
        fh.write(audio)
    print(f"Wrote {len(audio)} bytes to {out} via {provider}")


if __name__ == "__main__":
    asyncio.run(main())
