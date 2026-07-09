from __future__ import annotations

import json
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scanforge.safety import DEFAULT_MAX_TARGETS
from scanforge.web.history import HistoryStore, ScanOptions, default_history_path
from scanforge.web.jobs import ScanJobManager

STATIC_DIR = Path(__file__).with_name("static")


@dataclass(frozen=True, slots=True)
class WebResponse:
    status: HTTPStatus
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


class LocalScanForgeApp:
    def __init__(
        self,
        history_path: str | Path | None = None,
        history: HistoryStore | None = None,
    ) -> None:
        self.history = (
            history if history is not None else HistoryStore(history_path or default_history_path())
        )
        self.jobs = ScanJobManager(self.history)

    def handle(self, method: str, raw_path: str, body: bytes | None) -> WebResponse:
        path = urlparse(raw_path).path
        try:
            if method == "GET" and path == "/":
                return self._static_response("index.html", "text/html; charset=utf-8")
            if method == "GET" and path in {"/styles.css", "/app.js"}:
                content_type = (
                    "text/css; charset=utf-8" if path.endswith(".css") else "text/javascript"
                )
                return self._static_response(path.lstrip("/"), content_type)
            if method == "POST" and path == "/api/scans":
                return self._start_scan(body)
            if method == "GET" and path.startswith("/api/scans/"):
                return self._job_status(path)
            if method == "GET" and path == "/api/history":
                return self._json({"history": self.history.list_scans()})
            if method == "GET" and path.startswith("/api/history/"):
                return self._history_route("GET", path)
            if method == "POST" and path.startswith("/api/history/") and path.endswith("/rerun"):
                return self._history_route("POST", path)
        except ValueError as exc:
            return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except KeyError:
            return self._json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
        return self._json({"error": "Not found."}, HTTPStatus.NOT_FOUND)

    def _start_scan(self, body: bytes | None) -> WebResponse:
        data = self._read_json(body)
        options = ScanOptions(
            target=str(data.get("target", "")),
            ports=str(data.get("ports", "")),
            timeout=float(data.get("timeout", 1.0)),
            concurrency=int(data.get("concurrency", 100)),
            banner=bool(data.get("banner", False)),
            max_targets=int(data.get("max_targets", DEFAULT_MAX_TARGETS)),
            allow_large_scan=bool(data.get("allow_large_scan", False)),
        )
        job_id = self.jobs.start_scan(options)
        return self._json({"job_id": job_id}, HTTPStatus.ACCEPTED)

    def _job_status(self, path: str) -> WebResponse:
        job_id = path.removeprefix("/api/scans/")
        return self._json(self.jobs.get_job(job_id))

    def _history_route(self, method: str, path: str) -> WebResponse:
        pieces = path.removeprefix("/api/history/").split("/")
        scan_id = int(pieces[0])
        if len(pieces) == 1 and method == "GET":
            scan = self.history.get_scan(scan_id)
            if scan is None:
                raise KeyError(scan_id)
            return self._json(scan)
        if len(pieces) == 2 and method == "POST" and pieces[1] == "rerun":
            return self._json({"job_id": self.jobs.rerun(scan_id)}, HTTPStatus.ACCEPTED)
        if len(pieces) == 2 and method == "GET" and pieces[1] == "export.json":
            return WebResponse(
                HTTPStatus.OK,
                self.history.export_json(scan_id).encode(),
                {
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Disposition": f'attachment; filename="scanforge-{scan_id}.json"',
                },
            )
        if len(pieces) == 2 and method == "GET" and pieces[1] == "export.csv":
            return WebResponse(
                HTTPStatus.OK,
                self.history.export_csv(scan_id).encode(),
                {
                    "Content-Type": "text/csv; charset=utf-8",
                    "Content-Disposition": f'attachment; filename="scanforge-{scan_id}.csv"',
                },
            )
        raise KeyError(scan_id)

    def _static_response(self, filename: str, content_type: str) -> WebResponse:
        path = STATIC_DIR / filename
        if not path.exists():
            return WebResponse(
                HTTPStatus.OK,
                _fallback_index().encode(),
                {"Content-Type": content_type},
            )
        return WebResponse(HTTPStatus.OK, path.read_bytes(), {"Content-Type": content_type})

    def _read_json(self, body: bytes | None) -> dict[str, Any]:
        if not body:
            raise ValueError("Request body must be JSON.")
        try:
            payload = json.loads(body.decode())
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> WebResponse:
        return WebResponse(
            status,
            (json.dumps(payload, sort_keys=True) + "\n").encode(),
            {"Content-Type": "application/json; charset=utf-8"},
        )


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    history_path: str | Path | None = None,
) -> None:
    app = LocalScanForgeApp(history_path=history_path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._send(app.handle("GET", self.path, None))

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            self._send(app.handle("POST", self.path, self.rfile.read(length)))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send(self, response: WebResponse) -> None:
            self.send_response(response.status.value)
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ScanForge dashboard running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


def _fallback_index() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ScanForge</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main id="app">ScanForge</main>
  <script src="/app.js"></script>
</body>
</html>
"""
