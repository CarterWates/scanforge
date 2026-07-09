from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Sequence

from scanforge.models import PortResult, PortState, ScanReport, ScanSummary, Target
from scanforge.scanners.tcp import scan_tcp_port

ProgressCallback = Callable[[PortResult], None]


async def run_scan(
    targets: Sequence[Target],
    ports: Sequence[int],
    timeout: float = 1.0,
    concurrency: int = 100,
    grab_banners: bool = False,
    progress: ProgressCallback | None = None,
) -> ScanReport:
    if timeout <= 0:
        raise ValueError("Timeout must be greater than 0.")
    if concurrency < 1:
        raise ValueError("Concurrency must be at least 1.")
    if not targets:
        raise ValueError("At least one target is required.")
    if not ports:
        raise ValueError("At least one port is required.")

    started = time.perf_counter()
    semaphore = asyncio.Semaphore(concurrency)

    async def scan_one(target: Target, port: int) -> PortResult:
        async with semaphore:
            result = await scan_tcp_port(target, port, timeout, grab_banners)
            if progress is not None:
                progress(result)
            return result

    tasks = [scan_one(target, port) for target in targets for port in ports]
    results = tuple(await asyncio.gather(*tasks))
    summary = _summarize(results, len(targets), len(ports), time.perf_counter() - started)
    return ScanReport(summary=summary, results=results)


def _summarize(
    results: Sequence[PortResult],
    target_count: int,
    port_count: int,
    duration_seconds: float,
) -> ScanSummary:
    return ScanSummary(
        targets=target_count,
        ports=port_count,
        total_checks=len(results),
        open_ports=sum(1 for result in results if result.state == PortState.OPEN),
        closed_ports=sum(1 for result in results if result.state == PortState.CLOSED),
        filtered_ports=sum(1 for result in results if result.state == PortState.FILTERED),
        unknown_ports=sum(1 for result in results if result.state == PortState.UNKNOWN),
        duration_seconds=round(duration_seconds, 3),
    )
