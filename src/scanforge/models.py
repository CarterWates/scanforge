from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PortState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Target:
    value: str
    kind: str


@dataclass(frozen=True, slots=True)
class PortResult:
    target: str
    port: int
    state: PortState
    latency_ms: float
    banner: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ScanSummary:
    targets: int
    ports: int
    total_checks: int
    open_ports: int
    closed_ports: int
    filtered_ports: int
    unknown_ports: int
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class ScanReport:
    summary: ScanSummary
    results: tuple[PortResult, ...]
