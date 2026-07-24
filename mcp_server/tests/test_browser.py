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
