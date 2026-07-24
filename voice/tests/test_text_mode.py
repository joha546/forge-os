"""Text-mode pipeline tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from forge_memory.config import ForgeSettings
from forge_voice.pipeline import VoicePipeline


@pytest.mark.asyncio
async def test_run_text_turn_prints_and_skips_speak(capsys):
    settings = ForgeSettings(groq_api_key="test")
    llm = MagicMock()
    llm.chat_text = AsyncMock(return_value="Hello from Forge.")
    pipeline = VoicePipeline(
        settings=settings,
        stt=MagicMock(),
        llm=llm,
        mcp_client=None,
    )
    pipeline._speak = AsyncMock()

    reply = await pipeline.run_text_turn("Hi Forge", speak=False)

    assert reply == "Hello from Forge."
    llm.chat_text.assert_awaited_once()
    pipeline._speak.assert_not_awaited()
    captured = capsys.readouterr()
    assert "Forge: Hello from Forge." in captured.out


@pytest.mark.asyncio
async def test_run_text_turn_speaks_when_enabled():
    settings = ForgeSettings(groq_api_key="test")
    llm = MagicMock()
    llm.chat_text = AsyncMock(return_value="Spoken reply")
    pipeline = VoicePipeline(
        settings=settings,
        stt=MagicMock(),
        llm=llm,
        mcp_client=None,
    )
    pipeline._speak = AsyncMock()

    await pipeline.run_text_turn("Hello", speak=True)
    pipeline._speak.assert_awaited_once()
