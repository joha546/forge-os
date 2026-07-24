"""Memory tool tests."""

from pathlib import Path

from forge_mcp.tools import memory_tools
from forge_memory.config import ForgeSettings
from forge_memory.service import MemoryService


def test_memory_store_and_list(tmp_path: Path):
    settings = ForgeSettings(
        data_dir=tmp_path,
        memory_sqlite_path=tmp_path / "sqlite" / "forge.db",
        memory_chroma_path=tmp_path / "chroma",
    )
    service = MemoryService.from_settings(settings)
    result = memory_tools.memory_store(service, "remember forge-os")
    assert result["ok"] is True
    assert "id" in result

    listed = memory_tools.memory_list_recent(service, limit=5)
    assert listed["ok"] is True
    assert listed["items"][0]["text"] == "remember forge-os"


def test_notes_add_and_list(tmp_path: Path):
    settings = ForgeSettings(
        data_dir=tmp_path,
        memory_sqlite_path=tmp_path / "sqlite" / "forge.db",
        memory_chroma_path=tmp_path / "chroma",
    )
    service = MemoryService.from_settings(settings)
    added = memory_tools.notes_add(service, "Demo", "Run holiday script")
    assert added["ok"] is True

    listed = memory_tools.notes_list(service, limit=5)
    assert listed["items"][0]["title"] == "Demo"
