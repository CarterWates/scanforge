from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from scanforge.models import PortState, ScanReport

_STATE_STYLES = {
    PortState.OPEN: "bold green",
    PortState.CLOSED: "dim",
    PortState.FILTERED: "yellow",
    PortState.UNKNOWN: "red",
}


def build_results_table(report: ScanReport) -> Table:
    table = Table(title="Scan Results", show_lines=False)
    table.add_column("Target", overflow="fold")
    table.add_column("Port", justify="right")
    table.add_column("State")
    table.add_column("Latency", justify="right")
    table.add_column("Details", overflow="fold")

    for result in report.results:
        details = result.banner or result.error or ""
        table.add_row(
            result.target,
            str(result.port),
            f"[{_STATE_STYLES[result.state]}]{result.state.value}[/]",
            f"{result.latency_ms:.2f} ms",
            details,
        )

    return table


def render_summary(report: ScanReport) -> Panel:
    summary = report.summary
    body = (
        f"Targets: {summary.targets}  Ports: {summary.ports}  "
        f"Checks: {summary.total_checks}\n"
        f"Open: {summary.open_ports}  Closed: {summary.closed_ports}  "
        f"Filtered: {summary.filtered_ports}  Unknown: {summary.unknown_ports}\n"
        f"Duration: {summary.duration_seconds:.3f}s"
    )
    return Panel(body, title="Scan Summary", border_style="cyan")
