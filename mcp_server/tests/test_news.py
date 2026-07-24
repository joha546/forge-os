"""News tool tests."""

from unittest.mock import patch

from forge_mcp.tools import news as news_tools


def test_get_news_unknown_category():
    result = news_tools.get_news({"tech": []}, category="nope")
    assert result["ok"] is False
    assert result["code"] == "VALIDATION_ERROR"


def test_get_news_returns_items():
    feeds = {"tech": ["https://example.com/feed.xml"]}
    fake_entry = type(
        "Entry",
        (),
        {"title": "Headline", "link": "https://x", "published": "", "summary": "s"},
    )()
    fake_feed = {"title": "Example"}
    with patch("forge_mcp.tools.news.feedparser.parse") as parse:
        parse.return_value = type("Feed", (), {"feed": fake_feed, "entries": [fake_entry]})()
        result = news_tools.get_news(feeds, category="tech", max_items=1)
    assert result["ok"] is True
    assert result["items"][0]["title"] == "Headline"
