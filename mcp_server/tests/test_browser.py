"""Browser allowlist tests."""

import pytest
from forge_mcp.tools import browser


def test_host_allowed_matches_patterns():
    assert browser._host_allowed("https://example.com", ["example.com"], False)
    assert browser._host_allowed("https://en.wikipedia.org", ["*.wikipedia.org"], False)
    assert not browser._host_allowed("https://evil.com", ["example.com"], False)


@pytest.mark.asyncio
async def test_browser_navigate_denied():
    result = await browser.browser_navigate(
        "https://evil.com",
        allowlist=["example.com"],
        allow_all=False,
    )
    assert result["ok"] is False
    assert result["code"] == "ALLOWLIST_DENIED"


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser_inst = pw.chromium.launch(headless=True)
            browser_inst.close()
        return True
    except Exception:
        return False


@pytest.mark.asyncio
@pytest.mark.skipif(not _chromium_available(), reason="Playwright Chromium not installed")
async def test_browser_navigate_example_com_title():
    await browser.close_browser()
    try:
        result = await browser.browser_navigate(
            "https://example.com",
            allowlist=["example.com"],
            allow_all=False,
            headless=True,
        )
        assert result["ok"] is True, result
        assert "example" in result["title"].lower()
    finally:
        await browser.close_browser()
