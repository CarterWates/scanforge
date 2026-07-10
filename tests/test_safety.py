import pytest

from scanforge.models import Target
from scanforge.safety import enforce_target_limit


def _targets(count: int) -> tuple[Target, ...]:
    return tuple(Target(f"192.168.1.{index}", "ip") for index in range(1, count + 1))


def test_target_limit_allows_small_scan() -> None:
    enforce_target_limit(_targets(2), max_targets=2)


def test_target_limit_blocks_large_scan() -> None:
    with pytest.raises(ValueError, match="exceeds the limit"):
        enforce_target_limit(_targets(3), max_targets=2)


def test_target_limit_allows_explicit_override() -> None:
    enforce_target_limit(_targets(3), max_targets=2, allow_large_scan=True)
