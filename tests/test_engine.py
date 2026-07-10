import asyncio

from scanforge.engine import run_scan
from scanforge.models import PortState, Target


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.close()
    await writer.wait_closed()


def test_run_scan_returns_summary_and_results() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_handle_client, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            report = await run_scan((Target("127.0.0.1", "ip"),), (port,), timeout=1.0)
        finally:
            server.close()
            await server.wait_closed()

        assert report.summary.total_checks == 1
        assert report.summary.open_ports == 1
        assert report.results[0].state == PortState.OPEN

    asyncio.run(scenario())


def test_run_scan_invokes_progress_callback() -> None:
    async def scenario() -> None:
        seen = []
        server = await asyncio.start_server(_handle_client, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            await run_scan(
                (Target("127.0.0.1", "ip"),),
                (port,),
                timeout=1.0,
                progress=seen.append,
            )
        finally:
            server.close()
            await server.wait_closed()

        assert len(seen) == 1
        assert seen[0].state == PortState.OPEN

    asyncio.run(scenario())
