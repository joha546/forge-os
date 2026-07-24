"""TTS tests."""

from unittest.mock import AsyncMock, patch

import pytest
from forge_memory.config import ForgeSettings
from forge_voice.tts import TTSProviderError, synthesize


@pytest.mark.asyncio
async def test_synthesize_edge_returns_bytes():
    settings = ForgeSettings(tts_provider="edge", edge_tts_voice="en-US-GuyNeural")
    with patch("forge_voice.tts.synthesize_edge", new=AsyncMock(return_value=b"audio")):
        audio, provider = await synthesize("Hello", settings)
    assert audio == b"audio"
    assert provider == "edge"


@pytest.mark.asyncio
async def test_auto_falls_back_to_piper_on_edge_failure():
    settings = ForgeSettings(tts_provider="auto")
    with (
        patch(
            "forge_voice.tts.synthesize_edge",
            new=AsyncMock(side_effect=TTSProviderError("down")),
        ),
        patch("forge_voice.tts.synthesize_piper", return_value=b"wav"),
    ):
        audio, provider = await synthesize("Hello", settings)
    assert audio == b"wav"
    assert provider == "piper"


@pytest.mark.asyncio
async def test_offline_forces_piper():
    settings = ForgeSettings(tts_provider="auto", offline=True)
    with patch("forge_voice.tts.synthesize_piper", return_value=b"wav"):
        _, provider = await synthesize("Hello", settings)
    assert provider == "piper"
