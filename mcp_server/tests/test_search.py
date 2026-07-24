"""Search tool tests."""

from unittest.mock import MagicMock, patch

from forge_mcp.tools import search as search_tools


def test_web_search_requires_query():
    result = search_tools.web_search("  ")
    assert result["ok"] is False
    assert result["code"] == "VALIDATION_ERROR"


def test_web_search_returns_results():
    fake = [{"title": "Pipecat", "href": "https://pipecat.ai", "body": "Voice agents"}]
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__.return_value.text.return_value = fake
    with patch("forge_mcp.tools.search.DDGS", return_value=mock_ddgs):
        result = search_tools.web_search("Pipecat voice agents", max_results=1)
    assert result["ok"] is True
    assert result["backend"] == "ddg"
    assert result["results"][0]["title"] == "Pipecat"
    mock_ddgs.__enter__.return_value.text.assert_called()


def test_web_search_falls_through_empty_backend():
    mock_text = MagicMock(side_effect=[[], [{"title": "A", "href": "https://a.test", "body": "b"}]])
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__.return_value.text = mock_text
    with patch("forge_mcp.tools.search.DDGS", return_value=mock_ddgs):
        result = search_tools.web_search("news", max_results=1)
    assert result["ok"] is True
    assert result["results"][0]["title"] == "A"
    assert mock_text.call_count >= 2
