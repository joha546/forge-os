"""High-level memory API."""

from __future__ import annotations

from dataclasses import dataclass

from forge_memory.config import ForgeSettings
from forge_memory.sqlite_store import SQLiteStore
from forge_memory.vector_store import VectorStore


@dataclass
class MemoryService:
    sqlite: SQLiteStore
    vector: VectorStore

    @classmethod
    def from_settings(cls, settings: ForgeSettings) -> MemoryService:
        return cls(
            sqlite=SQLiteStore(settings.sqlite_path),
            vector=VectorStore(settings.chroma_path, settings.memory_collection),
        )

    def store(self, text: str, *, tags: list[str] | None = None, importance: int = 1) -> str:
        memory_id = self.sqlite.store_memory(text, tags=tags, importance=importance)
        self.vector.add(
            memory_id,
            text,
            metadata={
                "sqlite_id": memory_id,
                "tags": tags or [],
                "importance": importance,
                "created_at": self.sqlite.get_memory(memory_id)["created_at"],
            },
        )
        self.sqlite.update_chroma_id(memory_id, memory_id)
        return memory_id

    def recall(self, query: str, *, top_k: int = 5) -> list[dict]:
        return self.vector.query(query, top_k=top_k)

    def list_recent(self, limit: int = 10) -> list[dict]:
        items = self.sqlite.list_recent_memories(limit)
        return [
            {
                "id": item["id"],
                "text": item["text"],
                "created_at": item["created_at"],
                "tags": item["tags"],
            }
            for item in items
        ]
