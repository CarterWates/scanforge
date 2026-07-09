# ScanForge

ScanForge is a defensive network scanner built in Python. It focuses on clean engineering, safe defaults, and readable terminal reports.

> Only scan networks and systems you own or have explicit permission to assess.

## Features

- TCP connect scanning with no root privileges required
- Hostname, single IP, CIDR, and IPv4 range targets
- Port lists and ranges such as `22,80,443` or `1-1024`
- Async scanning with configurable timeouts and concurrency
- Optional lightweight banner grabbing
- Rich terminal tables and summaries
- JSON and CSV report output

## Install

```bash
python3 -m pip install -e ".[dev]"
```

## Examples

```bash
scanforge scan 127.0.0.1 --ports 22,80,443
scanforge scan 192.168.1.0/24 --ports 1-1024 --timeout 0.5 --concurrency 100
scanforge scan example.com --ports 80,443 --output json
scanforge scan 127.0.0.1 --ports 1-1024 --output csv > scan.csv
```

## Development

```bash
python3 -m pytest -v
python3 -m ruff check .
python3 -m mypy src/scanforge
```

## Roadmap

- Phase 1: polished terminal scanner, JSON/CSV exports, tests, and documentation
- Phase 2: local web dashboard with scan forms, progress, filtering, and downloads
- Later: scan profiles, HTML reports, historical comparisons, and optional privileged discovery modes
