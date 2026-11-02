import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from .config import Settings
from .models import ReadSnapshot
from .tags import ADDRESS_GROUPS, DWORD_TAGS

logger = logging.getLogger(__name__)


class PyXgtClient:
    """Small adapter that keeps the existing PyXGT command contract."""

    def __init__(self, settings: Settings) -> None:
        from PyXGT.LS import plc_ls

        self._connection = plc_ls(settings.plc_ip, settings.plc_port)
        self._plc_type = settings.plc_type

    def read(self, address: str, data_type: str) -> Any:
        result = self._connection.command(
            self._plc_type,
            "read",
            data_type,
            address,
        )
        if not isinstance(result, list) or len(result) != 1:
            raise ValueError(f"Unexpected PLC response for {address}: {result!r}")
        return result[0]

    def close(self) -> None:
        close = getattr(self._connection, "close", None)
        if callable(close):
            close()


class PlcReader:
    def __init__(
        self,
        settings: Settings,
        *,
        groups: Mapping[str, Mapping[str, str]] = ADDRESS_GROUPS,
        dword_tags: set[str] = DWORD_TAGS,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.groups = groups
        self.dword_tags = dword_tags
        if client_factory is not None:
            self._client_factory = client_factory
        else:
            self._client_factory = lambda: PyXgtClient(self.settings)
        self._client: Any | None = None
        self._values: dict[str, dict[str, Any]] = {
            group_name: {} for group_name in groups
        }
        self._errors: dict[str, str] = {}

    def read_once(self) -> ReadSnapshot:
        timestamp = datetime.now(timezone.utc)
        total_reads = sum(len(group) for group in self.groups.values())

        if self._client is None and not self._connect():
            return self._snapshot(
                timestamp,
                connected=False,
                successful_reads=0,
                failed_reads=total_reads,
            )

        successful_reads = 0
        failed_reads = 0

        for group_name, address_map in self.groups.items():
            for tag_name, address in address_map.items():
                key = f"{group_name}.{tag_name}"
                data_type = "dword" if tag_name in self.dword_tags else "word"
                try:
                    value = self._client.read(address, data_type)
                except Exception as exc:  # noqa: BLE001 - PyXGT exposes varied errors.
                    self._errors[key] = str(exc)
                    failed_reads += 1
                    logger.error(
                        "PLC read failed | group=%s | tag=%s | address=%s | "
                        "type=%s | error=%s",
                        group_name,
                        tag_name,
                        address,
                        data_type,
                        exc,
                    )
                    continue

                self._values[group_name][tag_name] = value
                self._errors.pop(key, None)
                successful_reads += 1

        if failed_reads and successful_reads == 0:
            logger.error("All PLC reads failed; reconnecting on the next cycle")
            self._close_client()

        return self._snapshot(
            timestamp,
            connected=successful_reads > 0,
            successful_reads=successful_reads,
            failed_reads=failed_reads,
        )

    def close(self) -> None:
        self._close_client()

    def _connect(self) -> bool:
        try:
            logger.info(
                "Connecting to PLC %s:%s (%s)",
                self.settings.plc_ip,
                self.settings.plc_port,
                self.settings.plc_type,
            )
            self._client = self._client_factory()
            logger.info("PLC connection created")
            self._errors.pop("connection", None)
            return True
        except Exception as exc:  # noqa: BLE001 - connection errors vary by PyXGT backend.
            self._client = None
            self._errors["connection"] = str(exc)
            logger.error("PLC connection failed: %s", exc)
            return False

    def _close_client(self) -> None:
        if self._client is None:
            return
        try:
            close = getattr(self._client, "close", None)
            if callable(close):
                close()
        except Exception:
            logger.exception("Error while closing PLC connection")
        finally:
            self._client = None

    def _snapshot(
        self,
        timestamp: datetime,
        *,
        connected: bool,
        successful_reads: int,
        failed_reads: int,
    ) -> ReadSnapshot:
        return ReadSnapshot(
            machine_id=self.settings.machine_id,
            timestamp=timestamp,
            connected=connected,
            values={group: dict(values) for group, values in self._values.items()},
            errors=dict(self._errors),
            successful_reads=successful_reads,
            failed_reads=failed_reads,
        )
