from __future__ import annotations

import asyncio


async def read_banner(reader: asyncio.StreamReader, timeout: float) -> str | None:
    try:
        data = await asyncio.wait_for(reader.read(256), timeout=timeout)
    except (TimeoutError, OSError, UnicodeDecodeError):
        return None

    if not data:
        return None

    return data.decode("utf-8", errors="replace").strip()[:200] or None
