import json
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from typer.testing import CliRunner

from scanforge.cli import app

runner = CliRunner()


@contextmanager
def local_tcp_server() -> Iterator[int]:
    ready = threading.Event()
    stop = threading.Event()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen()
        server.settimeout(0.1)
        port = server.getsockname()[1]

        def serve() -> None:
            ready.set()
            while not stop.is_set():
                try:
                    conn, _addr = server.accept()
                except TimeoutError:
                    continue
                with conn:
                    conn.sendall(b"cli-test\r\n")

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        ready.wait(timeout=1)
        try:
            yield port
        finally:
            stop.set()
            thread.join(timeout=1)


def test_cli_help_mentions_authorization() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "explicit permission" in result.output


def test_cli_rejects_invalid_port() -> None:
    result = runner.invoke(app, ["scan", "127.0.0.1", "--ports", "70000"])

    assert result.exit_code != 0
    assert "Port must be between" in result.output


def test_cli_json_scan_against_local_socket() -> None:
    with local_tcp_server() as port:
        result = runner.invoke(
            app,
            ["scan", "127.0.0.1", "--ports", str(port), "--output", "json"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["summary"]["open_ports"] == 1
    assert payload["results"][0]["state"] == "open"
