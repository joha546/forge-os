"""Transcript validation tests."""

from forge_voice.transcript import is_meaningful_transcript


def test_rejects_dots_and_empty():
    assert not is_meaningful_transcript("")
    assert not is_meaningful_transcript("   ")
    assert not is_meaningful_transcript(". . . .")
    assert not is_meaningful_transcript("...")
    assert not is_meaningful_transcript(", ,")


def test_accepts_real_speech():
    assert is_meaningful_transcript("What time is it?")
    assert is_meaningful_transcript("Hello Forge")
