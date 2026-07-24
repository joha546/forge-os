"""Persona tests."""

from forge_memory.config import ForgeSettings
from forge_voice.persona import build_system_prompt


def test_system_prompt_names_forge():
    settings = ForgeSettings(persona_name="Forge")
    prompt = build_system_prompt(settings)
    assert "Forge" in prompt
    assert "voice assistant" in prompt.lower()
