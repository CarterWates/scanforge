from __future__ import annotations

import ipaddress
import re

from scanforge.models import Target

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)


def parse_targets(spec: str, max_targets: int | None = None) -> tuple[Target, ...]:
    token = spec.strip()
    if not token:
        raise ValueError("Target specification cannot be empty.")

    if "/" in token:
        return _parse_cidr(token, max_targets)

    range_targets = _parse_ip_range(token, max_targets)
    if range_targets is not None:
        return range_targets

    try:
        ip = ipaddress.ip_address(token)
    except ValueError:
        return (_parse_hostname(token),)

    return (Target(value=str(ip), kind="ip"),)


def _parse_cidr(token: str, max_targets: int | None) -> tuple[Target, ...]:
    try:
        network = ipaddress.ip_network(token, strict=False)
    except ValueError as exc:
        raise ValueError(f"Invalid CIDR target: {token!r}.") from exc

    _enforce_expansion_limit(_network_size_upper_bound(network), max_targets)
    return tuple(Target(value=str(ip), kind="ip") for ip in network.hosts())


def _parse_ip_range(token: str, max_targets: int | None) -> tuple[Target, ...] | None:
    start_text, _, end_text = token.partition("-")
    if not start_text or not end_text:
        return None

    try:
        start = ipaddress.ip_address(start_text.strip())
        end = ipaddress.ip_address(end_text.strip())
    except ValueError:
        if _looks_like_address_range(start_text, end_text):
            raise ValueError(f"Invalid IP range target: {token!r}.") from None
        return None

    if start.version != end.version:
        raise ValueError("IP range endpoints must use the same IP version.")
    if int(start) > int(end):
        raise ValueError("IP range start must be less than or equal to the end.")

    _enforce_expansion_limit(int(end) - int(start) + 1, max_targets)
    return tuple(
        Target(value=str(ipaddress.ip_address(value)), kind="ip")
        for value in range(int(start), int(end) + 1)
    )


def _looks_like_address_range(start_text: str, end_text: str) -> bool:
    return any(_looks_like_address(piece.strip()) for piece in (start_text, end_text))


def _looks_like_address(value: str) -> bool:
    return bool(value) and all(char.isdigit() or char in ".:" for char in value)


def _network_size_upper_bound(network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> int:
    if network.version == 4 and network.prefixlen <= 30:
        return network.num_addresses - 2
    return network.num_addresses


def _enforce_expansion_limit(size: int, max_targets: int | None) -> None:
    if max_targets is not None and size > max_targets:
        raise ValueError(
            f"Target expands to {size} hosts, which exceeds the limit of {max_targets}."
        )


def _parse_hostname(token: str) -> Target:
    if all(char.isdigit() or char == "." for char in token):
        raise ValueError(f"Invalid IP address target: {token!r}.")
    if not _HOSTNAME_RE.match(token):
        raise ValueError(f"Invalid hostname target: {token!r}.")
    return Target(value=token.rstrip("."), kind="hostname")
