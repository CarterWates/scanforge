from __future__ import annotations

from collections.abc import Sequence

from scanforge.models import Target

DEFAULT_MAX_TARGETS = 256
AUTHORIZATION_NOTICE = (
    "Only scan networks and systems you own or have explicit permission to assess."
)


def enforce_target_limit(
    targets: Sequence[Target],
    max_targets: int = DEFAULT_MAX_TARGETS,
    allow_large_scan: bool = False,
) -> None:
    if max_targets < 1:
        raise ValueError("Maximum target limit must be at least 1.")

    if allow_large_scan:
        return

    if len(targets) > max_targets:
        raise ValueError(
            f"Target expands to {len(targets)} hosts, which exceeds the limit of {max_targets}. "
            "Use --allow-large-scan only for networks you are authorized to assess."
        )
