import time

import pytest

from scanforge.web.history import HistoryStore, ScanOptions
from scanforge.web.jobs import ScanJobManager


def _wait_for_finished(manager: ScanJobManager, job_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        payload = manager.get_job(job_id)
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError("scan job did not finish")


def test_start_scan_rejects_invalid_ports(tmp_path) -> None:
    manager = ScanJobManager(HistoryStore(tmp_path / "history.sqlite3"))

    with pytest.raises(ValueError, match="Port must be between"):
        manager.start_scan(ScanOptions(target="127.0.0.1", ports="70000"))


def test_scan_job_completes_and_persists_history(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    manager = ScanJobManager(store)

    job_id = manager.start_scan(
        ScanOptions(target="127.0.0.1", ports="1", timeout=0.05, concurrency=1)
    )
    payload = _wait_for_finished(manager, job_id)
    rows = store.list_scans()

    assert payload["status"] == "completed"
    assert payload["completed_checks"] == 1
    assert payload["summary"]["total_checks"] == 1
    assert len(rows) == 1
    assert rows[0]["total_checks"] == 1


def test_rerun_uses_historical_scan_options(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3")
    manager = ScanJobManager(store)
    first_job_id = manager.start_scan(
        ScanOptions(target="127.0.0.1", ports="1", timeout=0.05, concurrency=1)
    )
    first_payload = _wait_for_finished(manager, first_job_id)

    rerun_job_id = manager.rerun(int(first_payload["scan_id"]))
    rerun_payload = _wait_for_finished(manager, rerun_job_id)

    assert rerun_payload["status"] == "completed"
    assert rerun_payload["options"]["target"] == "127.0.0.1"
    assert rerun_payload["options"]["ports"] == "1"
