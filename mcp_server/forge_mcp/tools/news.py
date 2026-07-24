"""RSS news tool."""

from __future__ import annotations

import feedparser

from forge_mcp.results import err, ok


def _entry_value(entry, key: str, default: str = "") -> str:
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def get_news(
    feeds: dict[str, list[str]],
    category: str = "tech",
    max_items: int = 5,
) -> dict:
    if category not in feeds:
        return err(f"Unknown category: {category}", "VALIDATION_ERROR")
    items: list[dict] = []
    for url in feeds[category]:
        parsed = feedparser.parse(url)
        feed = parsed.feed
        if hasattr(feed, "get"):
            feed_title = feed.get("title", url)
        else:
            feed_title = getattr(feed, "title", url)
        for entry in parsed.entries[:max_items]:
            items.append(
                {
                    "title": _entry_value(entry, "title"),
                    "source": feed_title,
                    "url": _entry_value(entry, "link"),
                    "published": _entry_value(entry, "published"),
                    "summary": _entry_value(entry, "summary")[:500],
                }
            )
            if len(items) >= max_items:
                break
        if len(items) >= max_items:
            break
    return ok(items=items[:max_items])
