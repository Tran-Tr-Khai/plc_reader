import os
import re
import socket
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NetworkRoute:
    destination: str
    port: int
    local_ip: str | None
    interface_alias: str
    error: str | None = None


def check_tcp_connection(
    route: NetworkRoute,
    *,
    timeout_seconds: float = 2.0,
) -> tuple[bool, str | None]:
    if route.local_ip is None:
        return False, route.error or "local route is unavailable"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout_seconds)
            connection.bind((route.local_ip, 0))
            connection.connect((route.destination, route.port))
    except OSError as exc:
        return False, str(exc)
    return True, None


def route_for_endpoint(
    destination: str,
    port: int,
    *,
    interface_aliases: dict[str, str] | None = None,
) -> NetworkRoute:
    local_ip: str | None = None
    error: str | None = None
    try:
        address = socket.getaddrinfo(
            destination,
            port,
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
        )[0][4]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(address)
            local_ip = connection.getsockname()[0]
    except (OSError, IndexError) as exc:
        error = str(exc)

    aliases = interface_aliases if interface_aliases is not None else load_interface_aliases()
    alias = aliases.get(local_ip or "", "unknown")
    if local_ip == "127.0.0.1":
        alias = aliases.get(local_ip, "Loopback")
    return NetworkRoute(destination, port, local_ip, alias, error)


def load_interface_aliases() -> dict[str, str]:
    """Read Windows IPv4-to-interface mappings without adding a dependency."""
    if os.name != "nt":
        return {}

    try:
        result = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            check=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return {}

    aliases: dict[str, str] = {}
    interface_name: str | None = None
    ipv4_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    for line in result.stdout.splitlines():
        if line and not line[0].isspace() and line.rstrip().endswith(":"):
            heading = line.rstrip()[:-1]
            match = re.search(r"\badapter\s+(.+)$", heading, re.IGNORECASE)
            interface_name = match.group(1).strip() if match else heading.strip()
            continue

        if interface_name and "ipv4" in line.lower():
            match = ipv4_pattern.search(line)
            if match:
                aliases[match.group(0)] = interface_name
    return aliases
