"""SQLite persistence for memories and notes."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from forge_memory.schema import SCHEMA_SQL


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class SQLiteStore:
    path: Path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)
        return conn

    def store_memory(
        self,
        text: str,
        *,
        tags: list[str] | None = None,
        importance: int = 1,
        chroma_id: str | None = None,
    ) -> str:
        memory_id = str(uuid.uuid4())
        tags_json = json.dumps(tags or [])
        created_at = _utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, text, tags, importance, created_at, chroma_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (memory_id, text, tags_json, importance, created_at, chroma_id),
            )
        return memory_id

    def update_chroma_id(self, memory_id: str, chroma_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE memories SET chroma_id = ? WHERE id = ?",
                (chroma_id, memory_id),
            )

    def get_memory(self, memory_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            return None
        return _memory_row(row)

    def list_recent_memories(self, limit: int = 10) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_memory_row(row) for row in rows]

    def add_note(self, title: str, body: str) -> str:
        note_id = str(uuid.uuid4())
        created_at = _utc_now()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO notes (id, title, body, created_at) VALUES (?, ?, ?, ?)",
                (note_id, title, body, created_at),
            )
        return note_id

    def list_notes(self, limit: int = 20) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "body": row["body"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def log_turn(self, role: str, content: str) -> str:
        turn_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO turns (id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (turn_id, role, content, _utc_now()),
            )
        return turn_id


def _memory_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "text": row["text"],
        "tags": json.loads(row["tags"]),
        "importance": row["importance"],
        "created_at": row["created_at"],
        "chroma_id": row["chroma_id"],
    }
