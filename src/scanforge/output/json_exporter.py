from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from scanforge.models import PortResult, ScanReport, ScanSummary


def report_to_json(report: ScanReport) -> str:
    payload = {
        "summary": _summary_to_dict(report.summary),
        "results": [_result_to_dict(result) for result in report.results],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _summary_to_dict(summary: ScanSummary) -> dict[str, Any]:
    return asdict(summary)


def _result_to_dict(result: PortResult) -> dict[str, Any]:
    data = asdict(result)
    data["state"] = result.state.value
    return data
