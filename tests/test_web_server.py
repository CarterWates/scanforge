import json
from http import HTTPStatus

from scanforge.models import PortResult, PortState, ScanReport, ScanSummary
from scanforge.web.history import HistoryStore, ScanOptions
from scanforge.web.server import LocalScanForgeApp


def _report() -> ScanReport:
    return ScanReport(
        summary=ScanSummary(
            targets=1,
            ports=1,
            total_checks=1,
            open_ports=1,
            closed_ports=0,
            filtered_ports=0,
            unknown_ports=0,
            duration_seconds=0.1,
        ),
        results=(PortResult("127.0.0.1", 8080, PortState.OPEN, 1.0),),
    )


def test_index_serves_dashboard_shell(tmp_path) -> None:
    app = LocalScanForgeApp(history_path=tmp_path / "history.sqlite3")

    response = app.handle("GET", "/", None)

    assert response.status == HTTPStatus.OK
    assert "ScanForge" in response.body.decode()
    assert "styles.css" in response.body.decode()


def test_responses_include_basic_browser_protection_headers(tmp_path) -> None:
    app = LocalScanForgeApp(history_path=tmp_path / "history.sqlite3")

    response = app.handle("GET", "/", None)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"


def test_start_scan_route_returns_job_id(tmp_path) -> None:
    app = LocalScanForgeApp(history_path=tmp_path / "history.sqlite3")

    response = app.handle(
        "POST",
        "/api/scans",
        json.dumps({"target": "127.0.0.1", "ports": "1", "timeout": 0.05}).encode(),
    )
    payload = json.loads(response.body)

    assert response.status == HTTPStatus.ACCEPTED
    assert payload["job_id"]


def test_start_scan_route_returns_validation_error(tmp_path) -> None:
    app = LocalScanForgeApp(history_path=tmp_path / "history.sqlite3")

    response = app.handle(
        "POST",
        "/api/scans",
        json.dumps({"target": "127.0.0.1", "ports": "70000"}).encode(),
    )
    payload = json.loads(response.body)

    assert response.status == HTTPStatus.BAD_REQUEST
    assert "Port must be between" in payload["error"]


def test_history_and_export_routes(tmp_path) -> None:
    history = HistoryStore(tmp_path / "history.sqlite3")
    scan_id = history.save_completed_scan(ScanOptions(target="127.0.0.1", ports="8080"), _report())
    app = LocalScanForgeApp(history=history)

    list_response = app.handle("GET", "/api/history", None)
    detail_response = app.handle("GET", f"/api/history/{scan_id}", None)
    export_response = app.handle("GET", f"/api/history/{scan_id}/export.csv", None)

    assert json.loads(list_response.body)["history"][0]["id"] == scan_id
    assert json.loads(detail_response.body)["report"]["summary"]["open_ports"] == 1
    assert export_response.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert b"127.0.0.1,8080,open" in export_response.body
