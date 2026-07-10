# Design

ScanForge is a defensive TCP scanner with a small, layered Python architecture. The project is intentionally split into parsing, safety checks, scan orchestration, scanner implementations, and output rendering so each part can be tested and extended independently.

## Core Flow

1. The CLI accepts a target specification, port specification, timeout, concurrency, and output format.
2. Target and port parsers normalize input into typed values.
3. Safety checks enforce target expansion limits and keep the permission reminder visible.
4. The scan engine schedules TCP connection attempts with bounded concurrency.
5. Scanner functions return typed port results.
6. Output renderers convert the scan report to a terminal table, JSON, or CSV.

## Package Layout

```text
src/scanforge/
  cli.py
  engine.py
  models.py
  ports.py
  safety.py
  targets.py
  scanners/
  output/
```

## Phase 1 Scope

Phase 1 focuses on TCP connect scanning that works without root privileges. It supports hostnames, IP addresses, CIDR ranges, IPv4 ranges, configurable concurrency, timeouts, optional banner grabbing, Rich terminal output, JSON export, and CSV export.

## Phase 2 Direction

The next major milestone is a local browser dashboard that reuses the same scanner core. The dashboard should provide scan forms, live progress, filterable results, and downloadable reports.
