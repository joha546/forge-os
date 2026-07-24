#!/usr/bin/env python3
"""Text-only Groq round-trip."""

import asyncio
import sys

from forge_memory.config import load_settings
from forge_voice.llm import LLMClient


async def main() -> None:
    settings = load_settings()
    if not settings.groq_api_key:
        print("Set GROQ_API_KEY in .env (or export it), then retry.")
        sys.exit(1)
    client = LLMClient(settings)
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello in one short sentence."
    reply = await client.chat_text(prompt)
    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
