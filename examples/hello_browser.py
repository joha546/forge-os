#!/usr/bin/env python3
"""Fetch https://example.com title via browser tools (Playwright smoke)."""

from __future__ import annotations

import asyncio
import sys

from forge_memory.config import load_settings
from forge_mcp.tools import browser


async def main() -> int:
    settings = load_settings()
    try:
        result = await browser.browser_navigate(
            "https://example.com",
            allowlist=settings.browser_allowlist,
            allow_all=settings.browser_allow_all,
            headless=settings.browser_headless,
        )
        if not result.get("ok"):
            print(f"Navigate failed: {result}", file=sys.stderr)
            print("Hint: uv run playwright install chromium", file=sys.stderr)
            return 1
        title = result.get("title", "")
        print(f"url={result.get('url')}")
        print(f"title={title}")
        if "example" not in title.lower():
            print("Unexpected title (expected Example Domain).", file=sys.stderr)
            return 1
        return 0
    finally:
        await browser.close_browser()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
