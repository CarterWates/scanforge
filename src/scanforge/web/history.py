from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scanforge.models import ScanReport
from scanforge.output.csv_exporter import report_to_csv
from scanforge.output.json_exporter import report_to_json
from scanforge.web.schemas import JsonDict


@dataclass(frozen=True, slots=True)
class ScanOptions:
    target: str
    ports: str
    timeout: float = 1.0
    concurrency: int = 100
    banner: bool = False
    max_targets: int = 256
    allow_large_scan: bool = False


class HistoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def save_completed_scan(self, options: ScanOptions, report: ScanReport) -> int:
        summary_json = json.dumps(asdict(report.summary), sort_keys=True)
        report_json = report_to_json(report)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scans (
                    target_spec, port_spec, timeout, concurrency, banner,
                    max_targets, allow_large_scan, summary_json, report_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    options.target,
                    options.ports,
                    options.timeout,
                    options.concurrency,
                    int(options.banner),
                    options.max_targets,
                    int(options.allow_large_scan),
                    summary_json,
                    report_json,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return a scan id.")
            return int(cursor.lastrowid)

    def list_scans(self) -> list[JsonDict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, target_spec, port_spec, timeout, concurrency,
                       banner, max_targets, allow_large_scan, summary_json
                FROM scans
                ORDER BY datetime(created_at) DESC, id DESC
                """
            ).fetchall()
        return [self._row_to_list_item(row) for row in rows]

    def get_scan(self, scan_id: int) -> JsonDict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, created_at, target_spec, port_spec, timeout, concurrency,
                       banner, max_targets, allow_large_scan, report_json
                FROM scans
                WHERE id = ?
                """,
                (scan_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "options": {
                "target": row["target_spec"],
                "ports": row["port_spec"],
                "timeout": row["timeout"],
                "concurrency": row["concurrency"],
                "banner": bool(row["banner"]),
                "max_targets": row["max_targets"],
                "allow_large_scan": bool(row["allow_large_scan"]),
            },
            "report": json.loads(str(row["report_json"])),
        }

    def get_options(self, scan_id: int) -> ScanOptions | None:
        scan = self.get_scan(scan_id)
        if scan is None:
            return None
        options = scan["options"]
        return ScanOptions(
            target=str(options["target"]),
            ports=str(options["ports"]),
            timeout=float(options["timeout"]),
            concurrency=int(options["concurrency"]),
            banner=bool(options["banner"]),
            max_targets=int(options["max_targets"]),
            allow_large_scan=bool(options["allow_large_scan"]),
        )

    def export_json(self, scan_id: int) -> str:
        scan = self.get_scan(scan_id)
        if scan is None:
            raise KeyError(scan_id)
        return json.dumps(scan["report"], indent=2, sort_keys=True) + "\n"

    def export_csv(self, scan_id: int) -> str:
        scan = self.get_scan(scan_id)
        if scan is None:
            raise KeyError(scan_id)
        return _report_dict_to_csv(scan["report"])

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    target_spec TEXT NOT NULL,
                    port_spec TEXT NOT NULL,
                    timeout REAL NOT NULL,
                    concurrency INTEGER NOT NULL,
                    banner INTEGER NOT NULL,
                    max_targets INTEGER NOT NULL,
                    allow_large_scan INTEGER NOT NULL,
                    summary_json TEXT NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )

    def _row_to_list_item(self, row: sqlite3.Row) -> JsonDict:
        summary = json.loads(str(row["summary_json"]))
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "target_spec": row["target_spec"],
            "port_spec": row["port_spec"],
            "timeout": row["timeout"],
            "concurrency": row["concurrency"],
            "banner": bool(row["banner"]),
            "max_targets": row["max_targets"],
            "allow_large_scan": bool(row["allow_large_scan"]),
            "total_checks": summary["total_checks"],
            "open_ports": summary["open_ports"],
            "duration_seconds": summary["duration_seconds"],
        }


def _report_dict_to_csv(report: dict[str, Any]) -> str:
    from scanforge.models import PortResult, PortState, ScanReport, ScanSummary

    summary = ScanSummary(**report["summary"])
    results = tuple(
        PortResult(
            target=str(item["target"]),
            port=int(item["port"]),
            state=PortState(str(item["state"])),
            latency_ms=float(item["latency_ms"]),
            banner=item.get("banner"),
            error=item.get("error"),
        )
        for item in report["results"]
    )
    return report_to_csv(ScanReport(summary=summary, results=results))


def default_history_path() -> Path:
    return Path.cwd() / ".scanforge" / "history.sqlite3"
