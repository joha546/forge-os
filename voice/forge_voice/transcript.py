"""Helpers for cleaning / validating transcripts."""

from __future__ import annotations

import re

_NON_SPEECH = re.compile(r"^[\s\.\,\!\?\-\—\–\'\"…·•]+$")


def is_meaningful_transcript(text: str) -> bool:
    """Reject empty / punctuation-only Whisper hallucinations (e.g. '. . . .')."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    if _NON_SPEECH.match(cleaned):
        return False
    return any(ch.isalnum() for ch in cleaned)
