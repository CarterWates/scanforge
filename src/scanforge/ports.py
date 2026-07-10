from __future__ import annotations

MIN_PORT = 1
MAX_PORT = 65535


def parse_ports(spec: str) -> tuple[int, ...]:
    if not spec or not spec.strip():
        raise ValueError("Port specification cannot be empty.")

    ports: set[int] = set()
    for part in spec.split(","):
        token = part.strip()
        if not token:
            raise ValueError("Port specification contains an empty segment.")

        if "-" in token:
            ports.update(_parse_range(token))
        else:
            ports.add(_parse_single_port(token))

    return tuple(sorted(ports))


def _parse_range(token: str) -> range:
    pieces = token.split("-")
    if len(pieces) != 2 or not pieces[0] or not pieces[1]:
        raise ValueError(f"Invalid port range: {token!r}.")

    start = _parse_single_port(pieces[0])
    end = _parse_single_port(pieces[1])
    if start > end:
        raise ValueError(f"Port range starts after it ends: {token!r}.")

    return range(start, end + 1)


def _parse_single_port(token: str) -> int:
    try:
        port = int(token)
    except ValueError as exc:
        raise ValueError(f"Invalid port: {token!r}.") from exc

    if port < MIN_PORT or port > MAX_PORT:
        raise ValueError(f"Port must be between {MIN_PORT} and {MAX_PORT}: {port}.")
    return port
