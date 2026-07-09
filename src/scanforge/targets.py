from __future__ import annotations

import ipaddress
import re

from scanforge.models import Target

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)


def parse_targets(spec: str) -> tuple[Target, ...]:
    token = spec.strip()
    if not token:
        raise ValueError("Target specification cannot be empty.")

    if "/" in token:
        return _parse_cidr(token)

    if _looks_like_ip_range(token):
        return _parse_ip_range(token)

    try:
        ip = ipaddress.ip_address(token)
    except ValueError:
        return (_parse_hostname(token),)

    return (Target(value=str(ip), kind="ip"),)


def _parse_cidr(token: str) -> tuple[Target, ...]:
    try:
        network = ipaddress.ip_network(token, strict=False)
    except ValueError as exc:
        raise ValueError(f"Invalid CIDR target: {token!r}.") from exc

    return tuple(Target(value=str(ip), kind="ip") for ip in network.hosts())


def _looks_like_ip_range(token: str) -> bool:
    start, sep, end = token.partition("-")
    return bool(sep and start and end)


def _parse_ip_range(token: str) -> tuple[Target, ...]:
    start_text, _, end_text = token.partition("-")
    try:
        start = ipaddress.ip_address(start_text.strip())
        end = ipaddress.ip_address(end_text.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid IP range target: {token!r}.") from exc

    if start.version != end.version:
        raise ValueError("IP range endpoints must use the same IP version.")
    if int(start) > int(end):
        raise ValueError("IP range start must be less than or equal to the end.")

    return tuple(
        Target(value=str(ipaddress.ip_address(value)), kind="ip")
        for value in range(int(start), int(end) + 1)
    )


def _parse_hostname(token: str) -> Target:
    if all(char.isdigit() or char == "." for char in token):
        raise ValueError(f"Invalid IP address target: {token!r}.")
    if not _HOSTNAME_RE.match(token):
        raise ValueError(f"Invalid hostname target: {token!r}.")
    return Target(value=token.rstrip("."), kind="hostname")
