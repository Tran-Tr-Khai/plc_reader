import logging
import signal
from threading import Event

from .config import Settings
from .network import NetworkRoute, check_tcp_connection, route_for_endpoint
from .publisher import HttpPublisher
from .reader import PlcReader
from .tags import ADDRESS_GROUPS

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _print_network_routes(
    settings: Settings,
    upload_url: str | None,
) -> None:
    plc_route = route_for_endpoint(settings.plc_ip, settings.plc_port)
    print("\nNETWORK ROUTES")
    _print_network_route("PLC", plc_route)

    if upload_url is None:
        print("  Upload: disabled", flush=True)
        return

    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(upload_url)
        if parsed.hostname is None:
            raise ValueError("upload URL has no hostname")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        upload_route = route_for_endpoint(parsed.hostname, port)
    except ValueError as exc:
        print(f"  Upload: invalid URL ({exc})", flush=True)
        return
    _print_network_route("Upload", upload_route)


def _print_network_route(label: str, route: NetworkRoute) -> None:
    local = route.local_ip or "unresolved"
    tcp_ok, tcp_error = check_tcp_connection(route)
    if tcp_ok:
        status = "TCP OK"
    else:
        status = f"TCP FAIL: {tcp_error}"
    print(
        f"  {label}: {route.interface_alias} | {local} -> "
        f"{route.destination}:{route.port} | {status}",
        flush=True,
    )


def _print_snapshot(snapshot) -> None:
    print("\n" + "=" * 78)
    print(f"THỜI ĐIỂM: {snapshot.timestamp:%Y-%m-%d %H:%M:%S UTC}")
    print(
        f"KẾT NỐI: {'OK' if snapshot.connected else 'MẤT'} | "
        f"ĐỌC: {snapshot.successful_reads} OK, {snapshot.failed_reads} lỗi"
    )
    print("=" * 78)

    for group_name, address_map in ADDRESS_GROUPS.items():
        print(f"\n[{group_name}]")
        for tag_name, address in address_map.items():
            key = f"{group_name}.{tag_name}"
            if tag_name not in snapshot.values[group_name]:
                value, status = "N/A", "CHƯA ĐỌC ĐƯỢC"
            elif key in snapshot.errors:
                value, status = snapshot.values[group_name][tag_name], "STALE"
            else:
                value, status = snapshot.values[group_name][tag_name], "OK"
            print(f"  {tag_name:<42} {address:<8} = {value!s:<14} [{status}]")

    if snapshot.errors:
        print("\n--- LỖI ---")
        for key, error in snapshot.errors.items():
            print(f"  {key}: {error}")
    print("=" * 78, flush=True)


def main() -> None:
    settings = Settings.from_yaml()
    _configure_logging(settings.log_level)
    stop_event = Event()

    def request_stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)

    reader = PlcReader(settings)
    publisher = HttpPublisher(
        settings.upload_url,
        batch_url=settings.batch_url,
        timeout_seconds=settings.upload_timeout_seconds,
        token=settings.upload_token,
        outbox_path=settings.outbox_path,
        batch_size=settings.batch_size,
        max_outbox_bytes=settings.max_outbox_bytes,
    )
    _print_network_routes(settings, settings.upload_url)

    logger.info("Starting LS PLC reader for machine %s", settings.machine_id)
    if publisher.enabled:
        logger.info("PLC upload enabled: %s", settings.upload_url)
    else:
        logger.info("PLC upload disabled; running in reader-only mode")

    try:
        while not stop_event.is_set():
            interval = settings.reconnect_interval_seconds
            try:
                snapshot = reader.read_once()
                _print_snapshot(snapshot)
                publisher.publish(snapshot.payload())
                interval = (
                    settings.read_interval_seconds
                    if snapshot.connected
                    else settings.reconnect_interval_seconds
                )
            except Exception:
                logger.exception("Unexpected error in PLC cycle")

            stop_event.wait(interval)
    finally:
        reader.close()
        logger.info("LS PLC reader stopped")
