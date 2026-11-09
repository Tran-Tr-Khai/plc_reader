from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yml")


def _positive_int(name: str, raw: Any, default: int) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _non_negative_float(name: str, raw: Any, default: float) -> float:
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def _positive_float(name: str, raw: Any, default: float) -> float:
    value = _non_negative_float(name, raw, default)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _text(name: str, raw: Any, default: str) -> str:
    if raw is None:
        return default
    value = str(raw).strip()
    if not value:
        return default
    return value


def _optional_text(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


@dataclass(frozen=True, slots=True)
class Settings:
    plc_ip: str = "100.100.100.1"
    plc_port: int = 2004
    plc_type: str = "XGI"
    machine_id: str = "Tenter 1"
    read_interval_seconds: float = 15.0
    reconnect_interval_seconds: float = 30.0
    plc_socket_timeout_seconds: float = 5.0
    upload_url: str | None = None
    batch_url: str | None = None
    upload_token: str | None = None
    upload_timeout_seconds: float = 5.0
    batch_size: int = 100
    max_outbox_bytes: int = 500 * 1024 * 1024
    outbox_path: Path = Path("data/plc-outbox.jsonl")
    log_path: Path = Path("logs/plc_reader.log")
    log_max_bytes: int = 5 * 1024 * 1024
    log_backup_count: int = 5
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Settings":
        defaults = cls()
        try:
            raw_config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except OSError as exc:
            raise FileNotFoundError(f"Cannot read PLC config: {path}") from exc
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in PLC config: {path}") from exc

        if not isinstance(raw_config, Mapping):
            raise TypeError("PLC config root must be a YAML mapping")

        def relative_to_config(raw_path: str) -> Path:
            candidate = Path(raw_path)
            return candidate if candidate.is_absolute() else path.parent / candidate

        return cls(
            plc_ip=_text("plc_ip", raw_config.get("plc_ip"), defaults.plc_ip),
            plc_port=_positive_int(
                "plc_port", raw_config.get("plc_port"), defaults.plc_port
            ),
            plc_type=_text("plc_type", raw_config.get("plc_type"), defaults.plc_type),
            machine_id=_text(
                "machine_id", raw_config.get("machine_id"), defaults.machine_id
            ),
            read_interval_seconds=_positive_float(
                "read_interval_seconds",
                raw_config.get("read_interval_seconds"),
                defaults.read_interval_seconds,
            ),
            reconnect_interval_seconds=_positive_float(
                "reconnect_interval_seconds",
                raw_config.get("reconnect_interval_seconds"),
                defaults.reconnect_interval_seconds,
            ),
            plc_socket_timeout_seconds=_positive_float(
                "plc_socket_timeout_seconds",
                raw_config.get("plc_socket_timeout_seconds"),
                defaults.plc_socket_timeout_seconds,
            ),
            upload_url=_optional_text(raw_config.get("upload_url")),
            batch_url=_optional_text(raw_config.get("batch_url")),
            upload_token=_optional_text(raw_config.get("upload_token")),
            upload_timeout_seconds=_non_negative_float(
                "upload_timeout_seconds",
                raw_config.get("upload_timeout_seconds"),
                defaults.upload_timeout_seconds,
            ),
            batch_size=_positive_int(
                "batch_size", raw_config.get("batch_size"), defaults.batch_size
            ),
            max_outbox_bytes=_positive_int(
                "max_outbox_bytes",
                raw_config.get("max_outbox_bytes"),
                defaults.max_outbox_bytes,
            ),
            outbox_path=relative_to_config(
                _text(
                    "outbox_path",
                    raw_config.get("outbox_path"),
                    str(defaults.outbox_path),
                )
            ),
            log_path=relative_to_config(
                _text(
                    "log_path",
                    raw_config.get("log_path"),
                    str(defaults.log_path),
                )
            ),
            log_max_bytes=_positive_int(
                "log_max_bytes",
                raw_config.get("log_max_bytes"),
                defaults.log_max_bytes,
            ),
            log_backup_count=_positive_int(
                "log_backup_count",
                raw_config.get("log_backup_count"),
                defaults.log_backup_count,
            ),
            log_level=_text(
                "log_level", raw_config.get("log_level"), defaults.log_level
            ).upper(),
        )
