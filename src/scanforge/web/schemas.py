from __future__ import annotations

from dataclasses import asdict
from typing import Any

from scanforge.models import ScanReport

JsonDict = dict[str, Any]


def report_to_dict(report: ScanReport) -> JsonDict:
    return {
        "summary": asdict(report.summary),
        "results": [
            {
                **asdict(result),
                "state": result.state.value,
            }
            for result in report.results
        ],
    }
