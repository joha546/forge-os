"""Playwright browser tools (Phase 2)."""

from __future__ import annotations

import fnmatch
from urllib.parse import urlparse

from forge_mcp.results import err, ok

_browser = None
_page = None


def _host_allowed(url: str, allowlist: list[str], allow_all: bool) -> bool:
    if allow_all:
        return True
    host = urlparse(url).hostname or ""
    return any(fnmatch.fnmatch(host, pattern) for pattern in allowlist)


async def _ensure_browser(headless: bool = True):
    global _browser, _page
    if _browser is None:
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        _browser = await pw.chromium.launch(headless=headless)
        _page = await _browser.new_page()
    return _page


async def browser_navigate(
    url: str,
    *,
    allowlist: list[str],
    allow_all: bool = False,
    headless: bool = True,
) -> dict:
    if not _host_allowed(url, allowlist, allow_all):
        return err(f"URL not allowed: {url}", "ALLOWLIST_DENIED")
    try:
        page = await _ensure_browser(headless=headless)
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return ok(url=page.url, title=await page.title())
    except Exception as exc:
        return err(str(exc), "BACKEND_UNAVAILABLE")


async def browser_get_text(
    selector: str = "body",
    max_chars: int = 4000,
    *,
    headless: bool = True,
) -> dict:
    try:
        page = await _ensure_browser(headless=headless)
        text = await page.inner_text(selector)
        return ok(text=text[:max_chars])
    except Exception as exc:
        return err(str(exc), "BACKEND_UNAVAILABLE")


async def browser_snapshot(*, headless: bool = True) -> dict:
    try:
        page = await _ensure_browser(headless=headless)
        text = await page.inner_text("body")
        return ok(
            title=await page.title(),
            url=page.url,
            text_preview=text[:2000],
        )
    except Exception as exc:
        return err(str(exc), "BACKEND_UNAVAILABLE")
