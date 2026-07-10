from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal

from scanforge.engine import run_scan
from scanforge.models import PortResult, Target
from scanforge.ports import parse_ports
from scanforge.safety import enforce_target_limit
from scanforge.targets import parse_targets
from scanforge.web.history import HistoryStore, ScanOptions
from scanforge.web.schemas import JsonDict, report_to_dict

JobStatus = Literal["running", "completed", "failed"]


@dataclass
class _Job:
    id: str
    options: ScanOptions
    total_checks: int
    status: JobStatus = "running"
    completed_checks: int = 0
    results: list[dict[str, object]] = field(default_factory=list)
    summary: dict[str, object] | None = None
    error: str | None = None
    scan_id: int | None = None


class ScanJobManager:
    def __init__(self, history: HistoryStore) -> None:
        self.history = history
        self._jobs: dict[str, _Job] = {}
        self._lock = threading.Lock()

    def start_scan(self, options: ScanOptions) -> str:
        targets = parse_targets(
            options.target,
            max_targets=None if options.allow_large_scan else options.max_targets,
        )
        ports = parse_ports(options.ports)
        enforce_target_limit(targets, options.max_targets, options.allow_large_scan)
        if options.timeout <= 0:
            raise ValueError("Timeout must be greater than 0.")
        if options.concurrency < 1:
            raise ValueError("Concurrency must be at least 1.")

        job_id = uuid.uuid4().hex
        job = _Job(id=job_id, options=options, total_checks=len(targets) * len(ports))
        with self._lock:
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, targets, ports),
            daemon=True,
        )
        thread.start()
        return job_id

    def rerun(self, scan_id: int) -> str:
        options = self.history.get_options(scan_id)
        if options is None:
            raise KeyError(scan_id)
        return self.start_scan(options)

    def get_job(self, job_id: str) -> JsonDict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return self._job_payload(job)

    def _run_job(self, job_id: str, targets: Sequence[Target], ports: tuple[int, ...]) -> None:
        def progress(result: PortResult) -> None:
            with self._lock:
                job = self._jobs[job_id]
                job.completed_checks += 1
                job.results.append(
                    {
                        "target": result.target,
                        "port": result.port,
                        "state": result.state.value,
                        "latency_ms": result.latency_ms,
                        "banner": result.banner,
                        "error": result.error,
                    }
                )

        try:
            report = asyncio.run(
                run_scan(
                    targets,
                    ports,
                    timeout=self._jobs[job_id].options.timeout,
                    concurrency=self._jobs[job_id].options.concurrency,
                    grab_banners=self._jobs[job_id].options.banner,
                    progress=progress,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive guard around background work
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.error = str(exc)
            return

        scan_id = self.history.save_completed_scan(self._jobs[job_id].options, report)
        report_payload = report_to_dict(report)
        with self._lock:
            job = self._jobs[job_id]
            job.status = "completed"
            job.completed_checks = job.total_checks
            job.summary = report_payload["summary"]
            job.results = report_payload["results"]
            job.scan_id = scan_id

    def _job_payload(self, job: _Job) -> JsonDict:
        return {
            "id": job.id,
            "status": job.status,
            "options": asdict(job.options),
            "total_checks": job.total_checks,
            "completed_checks": job.completed_checks,
            "results": list(job.results),
            "summary": job.summary,
            "error": job.error,
            "scan_id": job.scan_id,
        }
