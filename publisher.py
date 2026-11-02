import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class HttpPublisher:
    """Optional JSON publisher with a small durable JSONL outbox."""

    def __init__(
        self,
        url: str | None,
        *,
        batch_url: str | None,
        timeout_seconds: float,
        token: str | None,
        outbox_path: Path,
        batch_size: int,
        max_outbox_bytes: int,
    ) -> None:
        self.url = url
        self.batch_url = batch_url
        self.timeout_seconds = timeout_seconds
        self.token = token
        self.outbox_path = outbox_path
        self.batch_size = batch_size
        self.max_outbox_bytes = max_outbox_bytes

    @property
    def enabled(self) -> bool:
        return self.url is not None

    def publish(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return

        self._flush_outbox()
        try:
            self._send(payload)
        except (HTTPError, URLError, OSError, ValueError) as exc:
            self._append(payload)
            logger.warning("PLC upload failed; payload queued locally: %s", exc)

    def _send(self, payload: dict[str, Any]) -> None:
        self._post(self.url, payload)

    def _send_batch(self, payloads: list[dict[str, Any]]) -> None:
        if self.batch_url is None:
            for payload in payloads:
                self._send(payload)
            return
        self._post(self.batch_url, payloads)

    def _post(self, url: str | None, payload: Any) -> None:
        if url is None:
            raise OSError("upload URL is not configured")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(url, data=body, headers=headers, method="POST")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            if not 200 <= response.status < 300:
                raise OSError(f"unexpected HTTP status {response.status}")

    def _flush_outbox(self) -> None:
        if not self.outbox_path.is_file():
            return

        lines = self.outbox_path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            batch_lines = lines[index : index + self.batch_size]
            try:
                payloads = [json.loads(line) for line in batch_lines]
                self._send_batch(payloads)
                index += len(batch_lines)
            except (HTTPError, URLError, OSError, ValueError) as exc:
                logger.warning("PLC outbox flush paused: %s", exc)
                break

        self._rewrite_outbox(lines[index:])

    def _append(self, payload: dict[str, Any]) -> None:
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        with self.outbox_path.open("a", encoding="utf-8") as outbox:
            outbox.write(json.dumps(payload, ensure_ascii=False) + "\n")
            outbox.flush()
            os.fsync(outbox.fileno())
        self._trim_outbox()

    def _trim_outbox(self) -> None:
        size = self.outbox_path.stat().st_size
        if size <= self.max_outbox_bytes:
            return

        bytes_to_drop = size - self.max_outbox_bytes
        dropped = 0
        dropped_bytes = 0
        with self.outbox_path.open("rb") as source:
            while dropped_bytes < bytes_to_drop:
                line = source.readline()
                if not line:
                    break
                dropped += 1
                dropped_bytes += len(line)

        temporary_path = self.outbox_path.with_suffix(".tmp")
        with self.outbox_path.open("rb") as source, temporary_path.open("wb") as target:
            for _ in range(dropped):
                source.readline()
            shutil.copyfileobj(source, target)
        os.replace(temporary_path, self.outbox_path)
        logger.error(
            "PLC outbox limit reached; dropped %d oldest payload(s)", dropped
        )

    def _rewrite_outbox(self, lines: list[str]) -> None:
        if not lines:
            try:
                self.outbox_path.unlink()
            except FileNotFoundError:
                pass
            return

        temporary_path = self.outbox_path.with_suffix(".tmp")
        temporary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(temporary_path, self.outbox_path)
