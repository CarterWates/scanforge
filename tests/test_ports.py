import pytest

from scanforge.ports import parse_ports


def test_parse_comma_separated_ports() -> None:
    assert parse_ports("22,80,443") == (22, 80, 443)


def test_parse_port_range() -> None:
    assert parse_ports("80-83") == (80, 81, 82, 83)


def test_parse_ports_deduplicates_and_sorts() -> None:
    assert parse_ports("443,80,80,22-23") == (22, 23, 80, 443)


@pytest.mark.parametrize("spec", ["", "0", "65536", "abc", "80-", "100-90", "22,,80"])
def test_parse_ports_rejects_invalid_specs(spec: str) -> None:
    with pytest.raises(ValueError):
        parse_ports(spec)
