"""MCP client for dynamic tool discovery."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)


class MCPClient:
    """Thin wrapper around an already-initialized ClientSession."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._session.list_tools()
        tools: list[dict[str, Any]] = []
        for tool in result.tools:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._session.call_tool(name, arguments)
        if not result.content:
            return {"ok": False, "error": "Empty tool result", "code": "INTERNAL_ERROR"}
        block = result.content[0]
        text = getattr(block, "text", None) or str(block)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"ok": True, "text": text}


@asynccontextmanager
async def open_mcp_client(url: str) -> AsyncIterator[MCPClient]:
    """Keep the SSE transport + session open for the whole voice process lifetime.

    Manual ``__aenter__`` on ``sse_client`` breaks anyio cancel scopes; always use
    this context manager from the same task that runs the agent loop.
    """
    async with sse_client(url) as streams:
        read, write = streams
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP session initialized (%s)", url)
            yield MCPClient(session)
