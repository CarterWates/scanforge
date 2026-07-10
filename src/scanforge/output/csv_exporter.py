from __future__ import annotations

import csv
import io

from scanforge.models import ScanReport

CSV_HEADERS = ("target", "port", "state", "latency_ms", "banner", "error")


def report_to_csv(report: ScanReport) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS)
    writer.writeheader()

    for result in report.results:
        writer.writerow(
            {
                "target": result.target,
                "port": result.port,
                "state": result.state.value,
                "latency_ms": result.latency_ms,
                "banner": result.banner or "",
                "error": result.error or "",
            }
        )

    return buffer.getvalue()
