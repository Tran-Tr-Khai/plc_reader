from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ReadSnapshot:
    machine_id: str
    timestamp: datetime
    connected: bool
    values: dict[str, dict[str, Any]]
    errors: dict[str, str]
    successful_reads: int
    failed_reads: int

    @property
    def is_complete(self) -> bool:
        """True only when every configured tag was read in this cycle."""
        return self.connected and self.failed_reads == 0

    def payload(self) -> dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
            "reading_values": self.values,
        }
