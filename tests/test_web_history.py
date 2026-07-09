import json

from scanforge.models import PortResult, PortState, ScanReport, ScanSummary
from scanforge.web.history import HistoryStore, ScanOptions
from scanforge.web.schemas import report_to_dict


def _report() -> ScanReport:
    return ScanReport(
        summary=ScanSummary(
            targets=1,
            ports=2,
            total_checks=2,
            open_ports=1,
            closed_ports=1,
            filtered_ports=0,
            unknown_ports=0,
            duration_seconds=0.25,
        ),
        results=(
            PortResult("127.0.0.1", 22, PortState.OPEN, 1.2, banner="ssh"),
            PortResult("127.0.0.1", 80, PortState.CLOSED, 0.8),
        ),
    )


def _options() -> ScanOptions:
    return ScanOptions(
        target="127.0.0.1",
        ports="22,80",
        timeout=0.5,
        concurrency=25,
        banner=True,
        max_targets=256,
        allow_large_scan=False,
    )


def test_report_to_dict_serializes_nested_dataclasses() -> None:
    payload = report_to_dict(_report())

    assert payload["summary"]["open_ports"] == 1
    assert payload["results"][0]["state"] == "open"
    assert payload["results"][0]["banner"] == "ssh"


def test_history_store_saves_lists_and_loads_report(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    scan_id = store.save_completed_scan(_options(), _report())

    rows = store.list_scans()
    loaded = store.get_scan(scan_id)

    assert rows[0]["id"] == scan_id
    assert rows[0]["target_spec"] == "127.0.0.1"
    assert rows[0]["open_ports"] == 1
    assert loaded is not None
    assert loaded["options"]["ports"] == "22,80"
    assert loaded["report"]["summary"]["total_checks"] == 2


def test_history_store_exports_json_and_csv(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    scan_id = store.save_completed_scan(_options(), _report())

    json_payload = json.loads(store.export_json(scan_id))
    csv_payload = store.export_csv(scan_id)

    assert json_payload["summary"]["open_ports"] == 1
    assert csv_payload.splitlines()[0] == "target,port,state,latency_ms,banner,error"
    assert "127.0.0.1,22,open,1.2,ssh," in csv_payload
