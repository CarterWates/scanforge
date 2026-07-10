import json

from rich.table import Table

from scanforge.models import PortResult, PortState, ScanReport, ScanSummary
from scanforge.output.csv_exporter import report_to_csv
from scanforge.output.json_exporter import report_to_json
from scanforge.output.terminal import build_results_table, render_summary


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
        results=(
            PortResult(
                target="127.0.0.1",
                port=8080,
                state=PortState.OPEN,
                latency_ms=1.25,
                banner="hello",
            ),
        ),
    )


def test_report_to_json_has_summary_and_results() -> None:
    payload = json.loads(report_to_json(_report()))

    assert payload["summary"]["open_ports"] == 1
    assert payload["results"][0]["state"] == "open"


def test_report_to_csv_has_stable_headers() -> None:
    output = report_to_csv(_report())

    assert output.splitlines()[0] == "target,port,state,latency_ms,banner,error"
    assert "127.0.0.1,8080,open,1.25,hello," in output


def test_build_results_table_returns_rich_table() -> None:
    table = build_results_table(_report())

    assert isinstance(table, Table)


def test_render_summary_returns_panel() -> None:
    panel = render_summary(_report())

    assert panel.title == "Scan Summary"
