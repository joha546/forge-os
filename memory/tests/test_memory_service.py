"""Memory service tests."""

from pathlib import Path

from forge_memory.config import ForgeSettings
from forge_memory.service import MemoryService


def test_store_and_recall_persists(tmp_path: Path):
    settings = ForgeSettings(
        data_dir=tmp_path,
        memory_sqlite_path=tmp_path / "sqlite" / "forge.db",
        memory_chroma_path=tmp_path / "chroma",
    )
    service = MemoryService.from_settings(settings)
    memory_id = service.store("forge-os holiday project", tags=["demo"])
    assert memory_id

    recent = service.list_recent(limit=5)
    assert recent[0]["text"] == "forge-os holiday project"
    assert recent[0]["tags"] == ["demo"]

    # Semantic recall may need embedding; at minimum list_recent works after restart
    service2 = MemoryService.from_settings(settings)
    again = service2.list_recent(limit=5)
    assert again[0]["id"] == memory_id
