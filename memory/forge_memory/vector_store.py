"""Chroma vector store for semantic memory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import chromadb


@dataclass
class VectorStore:
    path: Path
    collection_name: str = "forge_memories"
    _client: chromadb.ClientAPI | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self.path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.path))
        return self._client

    @property
    def collection(self):
        return self.client.get_or_create_collection(name=self.collection_name)

    def add(self, doc_id: str, text: str, *, metadata: dict) -> None:
        chroma_meta = dict(metadata)
        if "tags" in chroma_meta and isinstance(chroma_meta["tags"], list):
            chroma_meta["tags"] = json.dumps(chroma_meta["tags"])
        self.collection.upsert(ids=[doc_id], documents=[text], metadatas=[chroma_meta])

    def query(self, query_text: str, *, top_k: int = 5) -> list[dict]:
        if self.collection.count() == 0:
            return []
        result = self.collection.query(query_texts=[query_text], n_results=top_k)
        hits: list[dict] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        for doc_id, doc, meta, dist in zip(ids, docs, metas, dists, strict=False):
            tags_raw = meta.get("tags", "[]")
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
            score = 1.0 - float(dist) if dist is not None else 0.0
            hits.append(
                {
                    "id": meta.get("sqlite_id", doc_id),
                    "text": doc,
                    "score": score,
                    "created_at": meta.get("created_at", ""),
                    "tags": tags,
                }
            )
        return hits
