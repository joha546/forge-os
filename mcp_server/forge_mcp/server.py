"""FastMCP server entrypoint."""

from __future__ import annotations

import argparse
import json

from fastmcp import FastMCP
from forge_memory.config import load_settings
from forge_memory.service import MemoryService

from forge_mcp.tools import browser, memory_tools, news, search, system

mcp = FastMCP("forge-mcp")
_settings = load_settings()
_memory = MemoryService.from_settings(_settings)


@mcp.tool()
def system_time(timezone: str = "local") -> str:
    """Return current local or IANA timezone time."""
    return json.dumps(system.system_time(timezone))


@mcp.tool()
def memory_store(text: str, tags: list[str] | None = None, importance: int = 1) -> str:
    """Store a fact in semantic memory."""
    return json.dumps(memory_tools.memory_store(_memory, text, tags=tags, importance=importance))


@mcp.tool()
def memory_recall(query: str, top_k: int = 5) -> str:
    """Recall memories by semantic similarity."""
    return json.dumps(memory_tools.memory_recall(_memory, query, top_k=top_k))


@mcp.tool()
def memory_list_recent(limit: int = 10) -> str:
    """List recent stored memories."""
    return json.dumps(memory_tools.memory_list_recent(_memory, limit))


@mcp.tool()
def notes_add(title: str, body: str) -> str:
    """Add a structured note."""
    return json.dumps(memory_tools.notes_add(_memory, title, body))


@mcp.tool()
def notes_list(limit: int = 20) -> str:
    """List structured notes."""
    return json.dumps(memory_tools.notes_list(_memory, limit))


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web via DuckDuckGo."""
    return json.dumps(
        search.web_search(query, max_results, backend=_settings.search_backend)
    )


@mcp.tool()
def get_news(category: str = "tech", max_items: int = 5) -> str:
    """Fetch headlines from configured RSS feeds."""
    return json.dumps(news.get_news(_settings.news_feeds, category, max_items))


@mcp.tool()
async def browser_navigate(url: str) -> str:
    """Navigate browser to an allowlisted URL."""
    return json.dumps(
        await browser.browser_navigate(
            url,
            allowlist=_settings.browser_allowlist,
            allow_all=_settings.browser_allow_all,
            headless=_settings.browser_headless,
        )
    )


@mcp.tool()
async def browser_get_text(selector: str = "body", max_chars: int = 4000) -> str:
    """Get text from the current browser page."""
    return json.dumps(
        await browser.browser_get_text(selector, max_chars, headless=_settings.browser_headless)
    )


@mcp.tool()
async def browser_snapshot() -> str:
    """Snapshot title, URL, and text preview of current page."""
    return json.dumps(await browser.browser_snapshot(headless=_settings.browser_headless))


def main() -> None:
    parser = argparse.ArgumentParser(description="Forge MCP tool server")
    parser.add_argument("--transport", default=_settings.mcp_transport, choices=["sse", "stdio"])
    parser.add_argument("--host", default=_settings.mcp_host)
    parser.add_argument("--port", type=int, default=_settings.mcp_port)
    parser.add_argument("--list-tools", action="store_true")
    args = parser.parse_args()

    if args.list_tools:
        tools = [
            "system_time",
            "memory_store",
            "memory_recall",
            "memory_list_recent",
            "notes_add",
            "notes_list",
            "web_search",
            "get_news",
            "browser_navigate",
            "browser_get_text",
            "browser_snapshot",
        ]
        for name in tools:
            print(name)
        return

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
