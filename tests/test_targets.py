import pytest

from scanforge.models import Target
from scanforge.targets import parse_targets


def test_parse_single_ip() -> None:
    assert parse_targets("192.168.1.10") == (Target("192.168.1.10", "ip"),)


def test_parse_hostname() -> None:
    assert parse_targets("example.com") == (Target("example.com", "hostname"),)


def test_parse_hyphenated_hostname() -> None:
    assert parse_targets("dev-api.local") == (Target("dev-api.local", "hostname"),)


def test_parse_cidr_uses_host_addresses() -> None:
    assert parse_targets("192.168.1.0/30") == (
        Target("192.168.1.1", "ip"),
        Target("192.168.1.2", "ip"),
    )


def test_parse_inclusive_ip_range() -> None:
    assert parse_targets("192.168.1.10-192.168.1.12") == (
        Target("192.168.1.10", "ip"),
        Target("192.168.1.11", "ip"),
        Target("192.168.1.12", "ip"),
    )


def test_parse_cidr_rejects_expansion_over_limit() -> None:
    with pytest.raises(ValueError, match="exceeds the limit"):
        parse_targets("10.0.0.0/8", max_targets=256)


def test_parse_ip_range_rejects_expansion_over_limit() -> None:
    with pytest.raises(ValueError, match="exceeds the limit"):
        parse_targets("10.0.0.1-10.0.2.1", max_targets=256)


@pytest.mark.parametrize("spec", ["", "bad host name", "192.168.1.20-192.168.1.10", "300.1.1.1"])
def test_parse_targets_rejects_invalid_specs(spec: str) -> None:
    with pytest.raises(ValueError):
        parse_targets(spec)
