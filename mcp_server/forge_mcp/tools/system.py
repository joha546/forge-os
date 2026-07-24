"""System utility tools."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from forge_mcp.results import err, ok


def system_time(timezone: str = "local") -> dict:
    try:
        if timezone == "local":
            now = datetime.now().astimezone()
            tz_name = str(now.tzinfo) if now.tzinfo else "local"
        else:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
            tz_name = timezone
    except Exception as exc:
        return err(str(exc), "VALIDATION_ERROR")

    return ok(
        iso=now.isoformat(),
        human=now.strftime("%A, %B %d, %Y, %I:%M %p"),
        timezone=tz_name,
    )
