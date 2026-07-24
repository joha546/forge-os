"""Shared MCP tool result helpers."""

from __future__ import annotations

from typing import Any


def ok(**fields: Any) -> dict[str, Any]:
    return {"ok": True, **fields}


def err(message: str, code: str = "INTERNAL_ERROR") -> dict[str, Any]:
    return {"ok": False, "error": message, "code": code}
