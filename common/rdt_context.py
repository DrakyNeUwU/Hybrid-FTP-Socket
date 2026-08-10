"""Shared transfer context used by Roles A, B and C."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
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
    transfer_type: str = "I"


START_METADATA = struct.Struct("!Qcc")
LEGACY_START_METADATA = struct.Struct("!Q")


def encode_start_metadata(
    total_bytes: int | None,
    transfer_mode: str = "S",
    transfer_type: str = "I",
) -> bytes:
    """Encode logical size plus negotiated MODE/TYPE without changing the header."""
    mode = str(transfer_mode).strip().upper()
    representation = str(transfer_type).strip().upper()
    if mode not in ("S", "B", "C"):
        raise ValueError(f"Invalid START transfer mode: {transfer_mode!r}")
    if representation not in ("A", "I"):
        raise ValueError(f"Invalid START transfer type: {transfer_type!r}")
    return START_METADATA.pack(
        total_bytes if total_bytes is not None else 0,
        mode.encode("ascii"),
        representation.encode("ascii"),
    )


def decode_start_metadata(payload: bytes) -> tuple[int, str | None, str | None]:
    """Decode current metadata while retaining low-level legacy compatibility."""
    if len(payload) == LEGACY_START_METADATA.size:
        (total_bytes,) = LEGACY_START_METADATA.unpack(payload)
        return total_bytes, None, None
    if len(payload) != START_METADATA.size:
        raise ValueError(f"Invalid START metadata length: {len(payload)}")
    total_bytes, raw_mode, raw_type = START_METADATA.unpack(payload)
    try:
        mode = raw_mode.decode("ascii")
        representation = raw_type.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("START metadata is not ASCII") from error
    if mode not in ("S", "B", "C") or representation not in ("A", "I"):
        raise ValueError("START metadata contains unsupported MODE/TYPE")
    return total_bytes, mode, representation


def normalize_transfer_id(value: str | int) -> int:
    """Convert a public transfer ID into the unsigned 32-bit RDT wire value."""
    if isinstance(value, str):
        return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)
    return int(value) & 0xFFFFFFFF
