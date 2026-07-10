import asyncio

from scanforge.models import PortState, Target
from scanforge.scanners.tcp import scan_tcp_port


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.write(b"test-service\r\n")
    await writer.drain()
    writer.close()
    await writer.wait_closed()


def test_scan_tcp_port_detects_open_port() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_handle_client, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            result = await scan_tcp_port(Target("127.0.0.1", "ip"), port, timeout=1.0)
        finally:
            server.close()
            await server.wait_closed()

        assert result.state == PortState.OPEN
        assert result.port == port

    asyncio.run(scenario())


def test_scan_tcp_port_can_grab_banner() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_handle_client, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            result = await scan_tcp_port(
                Target("127.0.0.1", "ip"),
                port,
                timeout=1.0,
                grab_banner=True,
            )
        finally:
            server.close()
            await server.wait_closed()

        assert result.state == PortState.OPEN
        assert result.banner == "test-service"

    asyncio.run(scenario())
