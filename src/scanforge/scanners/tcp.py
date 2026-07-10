from __future__ import annotations

import asyncio
import time

from scanforge.models import PortResult, PortState, Target
from scanforge.scanners.banners import read_banner


async def scan_tcp_port(
    target: Target,
    port: int,
    timeout: float,
    grab_banner: bool = False,
) -> PortResult:
    start = time.perf_counter()
    writer: asyncio.StreamWriter | None = None

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target.value, port),
            timeout=timeout,
        )
        banner = await read_banner(reader, timeout) if grab_banner else None
        return PortResult(
            target=target.value,
            port=port,
            state=PortState.OPEN,
            latency_ms=_elapsed_ms(start),
            banner=banner,
        )
    except ConnectionRefusedError as exc:
        return PortResult(
            target=target.value,
            port=port,
            state=PortState.CLOSED,
            latency_ms=_elapsed_ms(start),
            error=str(exc) or "connection refused",
        )
    except TimeoutError as exc:
        return PortResult(
            target=target.value,
            port=port,
            state=PortState.FILTERED,
            latency_ms=_elapsed_ms(start),
            error=str(exc) or "connection timed out",
        )
    except OSError as exc:
        return PortResult(
            target=target.value,
            port=port,
            state=PortState.UNKNOWN,
            latency_ms=_elapsed_ms(start),
            error=str(exc),
        )
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
