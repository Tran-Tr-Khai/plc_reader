import logging
import signal
from logging.handlers import RotatingFileHandler
from threading import Event

from .config import Settings
from .network import NetworkRoute, check_tcp_connection, route_for_endpoint
from .publisher import HttpPublisher
from .reader import PlcReader

logger = logging.getLogger(__name__)


def _configure_logging(settings: Settings) -> None:
    numeric_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[file_handler],
        force=True,
    )


def _log_network_routes(settings: Settings, upload_url: str | None) -> None:
    plc_route = route_for_endpoint(settings.plc_ip, settings.plc_port)
    _log_network_route("PLC", plc_route)

    if upload_url is None:
        logger.info("Network route | upload=disabled")
        return

    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(upload_url)
        if parsed.hostname is None:
            raise ValueError("upload URL has no hostname")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        upload_route = route_for_endpoint(parsed.hostname, port)
    except ValueError as exc:
        logger.warning("Network route | upload=invalid | error=%s", exc)
        return
    _log_network_route("Upload", upload_route)


def _log_network_route(label: str, route: NetworkRoute) -> None:
    tcp_ok, tcp_error = check_tcp_connection(route)
    logger.info(
        "Network route | %s | interface=%s | local=%s | destination=%s:%s | tcp=%s",
        label,
        route.interface_alias,
        route.local_ip or "unresolved",
        route.destination,
        route.port,
        "ok" if tcp_ok else f"failed ({tcp_error})",
    )


def main() -> None:
    settings = Settings.from_yaml()
    _configure_logging(settings)
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
    _log_network_routes(settings, settings.upload_url)

    logger.info("Starting LS PLC reader for machine %s", settings.machine_id)
    if publisher.enabled:
        logger.info("PLC upload enabled: %s", settings.upload_url)
    else:
        logger.info("PLC upload disabled; running in reader-only mode")

    upload_paused = False
    try:
        while not stop_event.is_set():
            interval = settings.reconnect_interval_seconds
            try:
                snapshot = reader.read_once()
                if publisher.enabled:
                    if snapshot.is_complete:
                        if upload_paused:
                            logger.info("PLC reads recovered; upload resumed")
                        publisher.publish(snapshot.payload())
                        upload_paused = False
                    elif not upload_paused:
                        logger.warning(
                            "PLC upload paused until a complete snapshot is available | "
                            "connected=%s | successful=%s | failed=%s",
                            snapshot.connected,
                            snapshot.successful_reads,
                            snapshot.failed_reads,
                        )
                        upload_paused = True
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
