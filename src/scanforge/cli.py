from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from scanforge.engine import run_scan
from scanforge.models import ScanReport, Target
from scanforge.output.csv_exporter import report_to_csv
from scanforge.output.json_exporter import report_to_json
from scanforge.output.terminal import build_results_table, render_summary
from scanforge.ports import parse_ports
from scanforge.safety import AUTHORIZATION_NOTICE, DEFAULT_MAX_TARGETS, enforce_target_limit
from scanforge.targets import parse_targets

app = typer.Typer(
    add_completion=False,
    help=f"Defensive TCP network scanner. {AUTHORIZATION_NOTICE}",
)
console = Console()


@app.callback()
def main() -> None:
    """Defensive TCP network scanner."""


@app.command()
def scan(
    target: Annotated[str, typer.Argument(help="Hostname, IP, CIDR, or IPv4 range to scan.")],
    ports: Annotated[str, typer.Option("--ports", "-p", help="Ports such as 22,80,443 or 1-1024.")],
    timeout: Annotated[float, typer.Option(help="Connection timeout in seconds.")] = 1.0,
    concurrency: Annotated[int, typer.Option(help="Maximum concurrent connection attempts.")] = 100,
    output: Annotated[str, typer.Option(help="Output format: table, json, or csv.")] = "table",
    banner: Annotated[
        bool,
        typer.Option("--banner/--no-banner", help="Attempt banner grabbing."),
    ] = False,
    max_targets: Annotated[
        int,
        typer.Option(help="Maximum expanded targets without override."),
    ] = DEFAULT_MAX_TARGETS,
    allow_large_scan: Annotated[
        bool,
        typer.Option(help="Allow target expansion beyond --max-targets."),
    ] = False,
) -> None:
    """Scan TCP ports on authorized targets."""

    try:
        parsed_targets = parse_targets(
            target,
            max_targets=None if allow_large_scan else max_targets,
        )
        parsed_ports = parse_ports(ports)
        enforce_target_limit(parsed_targets, max_targets, allow_large_scan)
        _validate_scan_options(timeout, concurrency, output)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if output == "table":
        report = _run_table_scan(parsed_targets, parsed_ports, timeout, concurrency, banner)
        console.print(render_summary(report))
        console.print(build_results_table(report))
        return

    report = asyncio.run(
        run_scan(
            parsed_targets,
            parsed_ports,
            timeout=timeout,
            concurrency=concurrency,
            grab_banners=banner,
        )
    )
    if output == "json":
        typer.echo(report_to_json(report))
    else:
        typer.echo(report_to_csv(report), nl=False)


def _validate_scan_options(timeout: float, concurrency: int, output: str) -> None:
    if timeout <= 0:
        raise ValueError("Timeout must be greater than 0.")
    if concurrency < 1:
        raise ValueError("Concurrency must be at least 1.")
    if output not in {"table", "json", "csv"}:
        raise ValueError("Output must be one of: table, json, csv.")


def _run_table_scan(
    targets: Sequence[Target],
    ports: tuple[int, ...],
    timeout: float,
    concurrency: int,
    banner: bool,
) -> ScanReport:
    total = len(targets) * len(ports)
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Scanning[/]"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("scan", total=total)

        def advance(_result: object) -> None:
            progress.update(task_id, advance=1)

        return asyncio.run(
            run_scan(
                targets,
                ports,
                timeout=timeout,
                concurrency=concurrency,
                grab_banners=banner,
                progress=advance,
            )
        )


if __name__ == "__main__":
    app()
