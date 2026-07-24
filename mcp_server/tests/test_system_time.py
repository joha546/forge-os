"""system_time tool tests."""

from forge_mcp.tools import system as system_tools


def test_system_time_local_ok():
    result = system_tools.system_time("local")
    assert result["ok"] is True
    assert "iso" in result
    assert "human" in result
    assert "timezone" in result


def test_system_time_invalid_timezone():
    result = system_tools.system_time("Not/AZone")
    assert result["ok"] is False
    assert result["code"] == "VALIDATION_ERROR"
