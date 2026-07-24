"""Web search tool."""

from __future__ import annotations

import logging

from ddgs import DDGS

from forge_mcp.results import err, ok

logger = logging.getLogger(__name__)

# Prefer DuckDuckGo; fall through if a backend returns nothing / errors.
_BACKEND_CHAIN = ("duckduckgo", "auto", "bing", "yahoo")


def web_search(query: str, max_results: int = 5, *, backend: str = "ddg") -> dict:
    if not query.strip():
        return err("query is required", "VALIDATION_ERROR")
    if backend not in {"ddg", "searxng"}:
        return err(f"Unsupported backend: {backend}", "BACKEND_UNAVAILABLE")
    if backend == "searxng":
        return err("SearXNG backend not configured in this build", "BACKEND_UNAVAILABLE")

    max_results = max(1, min(int(max_results), 10))
    last_error: Exception | None = None

    try:
        with DDGS() as ddgs:
            for provider in _BACKEND_CHAIN:
                try:
                    raw = list(ddgs.text(query, max_results=max_results, backend=provider))
                except Exception as exc:  # noqa: BLE001 — try next provider
                    last_error = exc
                    logger.warning("web_search backend=%s failed: %s", provider, exc)
                    continue
                results = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                    }
                    for item in raw
                    if item.get("title") or item.get("href")
                ]
                if results:
                    logger.info(
                        "web_search query=%r backend=%s results=%d",
                        query,
                        provider,
                        len(results),
                    )
                    return ok(backend="ddg", results=results)
                logger.warning("web_search backend=%s returned 0 results", provider)
    except Exception as exc:  # noqa: BLE001
        logger.exception("web_search failed")
        return err(str(exc), "BACKEND_UNAVAILABLE")

    if last_error is not None:
        return err(str(last_error), "BACKEND_UNAVAILABLE")
    return ok(backend="ddg", results=[])
