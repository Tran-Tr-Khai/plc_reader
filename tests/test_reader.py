import logging
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from plc_reader.config import Settings
from plc_reader.main import _configure_logging
from plc_reader.models import ReadSnapshot
from plc_reader.reader import PlcReader, PyXgtClient


class _Socket:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _PyXgtWrapper:
    def __init__(self) -> None:
        self.conn_class = _Socket()


class _ResetError(OSError):
    winerror = 10054


class _ResettingClient:
    def __init__(self) -> None:
        self.closed = False

    def read(self, address: str, data_type: str) -> int:
        raise _ResetError("connection reset")

    def close(self) -> None:
        self.closed = True


class ReaderTests(unittest.TestCase):
    def test_pyxgt_close_closes_the_underlying_socket(self) -> None:
        client = object.__new__(PyXgtClient)
        client._connection = _PyXgtWrapper()

        client.close()

        self.assertTrue(client._connection.conn_class.closed)

    def test_connection_reset_stops_the_cycle_after_one_error(self) -> None:
        client = _ResettingClient()
        reader = PlcReader(
            Settings(),
            groups={"group": {"first": "M1", "second": "M2"}},
            client_factory=lambda: client,
        )

        with self.assertLogs("plc_reader.reader", logging.ERROR) as captured:
            snapshot = reader.read_once()

        self.assertFalse(snapshot.connected)
        self.assertEqual(snapshot.successful_reads, 0)
        self.assertEqual(snapshot.failed_reads, 2)
        self.assertEqual(list(snapshot.errors), ["connection"])
        self.assertTrue(client.closed)
        self.assertEqual(len(captured.records), 1)

    def test_relative_paths_are_resolved_from_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            config_path.write_text(
                "outbox_path: data/outbox.jsonl\nlog_path: logs/reader.log\n",
                encoding="utf-8",
            )

            settings = Settings.from_yaml(config_path)

        self.assertEqual(settings.outbox_path, config_path.parent / "data/outbox.jsonl")
        self.assertEqual(settings.log_path, config_path.parent / "logs/reader.log")

    def test_incomplete_snapshot_is_not_uploadable(self) -> None:
        snapshot = ReadSnapshot(
            machine_id="Tenter 1",
            timestamp=datetime.now(timezone.utc),
            connected=True,
            values={},
            errors={"group.tag": "read failed"},
            successful_reads=1,
            failed_reads=1,
        )

        self.assertFalse(snapshot.is_complete)

    def test_application_log_rotates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "plc_reader.log"
            settings = replace(
                Settings(),
                log_path=log_path,
                log_max_bytes=100,
                log_backup_count=1,
                log_level="WARNING",
            )

            _configure_logging(settings)
            logging.getLogger("test.rotation").warning("x" * 200)
            logging.getLogger("test.rotation").warning("y" * 200)
            logging.shutdown()

            self.assertTrue(log_path.is_file())
            self.assertTrue(log_path.with_name("plc_reader.log.1").is_file())
