"""Memory MCP tools."""

from __future__ import annotations

from forge_memory.service import MemoryService

from forge_mcp.results import err, ok


def memory_store(
    service: MemoryService,
    text: str,
    tags: list[str] | None = None,
    importance: int = 1,
) -> dict:
    if not text.strip():
        return err("text is required", "VALIDATION_ERROR")
    memory_id = service.store(text, tags=tags or [], importance=importance)
    return ok(id=memory_id)


def memory_recall(service: MemoryService, query: str, top_k: int = 5) -> dict:
    if not query.strip():
        return err("query is required", "VALIDATION_ERROR")
    hits = service.recall(query, top_k=top_k)
    return ok(hits=hits)


def memory_list_recent(service: MemoryService, limit: int = 10) -> dict:
    return ok(items=service.list_recent(limit))


def notes_add(service: MemoryService, title: str, body: str) -> dict:
    if not title.strip():
        return err("title is required", "VALIDATION_ERROR")
    note_id = service.sqlite.add_note(title, body)
    return ok(id=note_id)


def notes_list(service: MemoryService, limit: int = 20) -> dict:
    return ok(items=service.sqlite.list_notes(limit))
