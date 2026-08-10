"""Shared transfer context used by Roles A, B and C."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import threading
from typing import Literal


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int
    mode: Literal["ACTIVE", "PASSIVE"] = "PASSIVE"


@dataclass(frozen=True)
class TransferContext:
    transfer_id: str
    operation: Literal["RETR", "STOR", "STOU", "APPE"]
    session_id: str
    endpoint: Endpoint
    cancel_event: threading.Event
    chunk_size: int = 1024
    timeout_seconds: float = 0.5
    retry_limit: int = 10
    max_timeouts: int = 10
    window_size: int = 4
    total_bytes: int | None = None
    transfer_mode: str = "S"


def normalize_transfer_id(value: str | int) -> int:
    """Convert a public transfer ID into the unsigned 32-bit RDT wire value."""
    if isinstance(value, str):
        return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)
    return int(value) & 0xFFFFFFFF
