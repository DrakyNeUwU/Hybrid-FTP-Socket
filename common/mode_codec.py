"""FTP transmission-mode codecs (RFC 959 §3.4): Stream, Block and Compressed.

Role A implements MODE S/B/C as a per-session, per-transfer transformation that
lives *outside* the canonical RDT wire protocol: encoding happens before RDT
packetization and decoding happens after ordered RDT delivery and checksum
validation.  Filesystem (Role C) always observes logical, decoded bytes.

All encoders/decoders are streaming generators so a whole file is never loaded
into RAM.  Malformed frames raise :class:`ModeCodecError` (an FTP 426
``FilesystemOperationError``) so the transfer boundary can fail atomically
without committing partial output.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable, Iterator

from common.filesystem_service import FilesystemOperationError

MODE_STREAM = "S"
MODE_BLOCK = "B"
MODE_COMPRESSED = "C"
VALID_MODES = frozenset((MODE_STREAM, MODE_BLOCK, MODE_COMPRESSED))

# Wire chunk budget: RDT receiver buffers up to 1024 payload bytes per datagram,
# so every emitted wire chunk must stay within that budget.
WIRE_CHUNK_SIZE = 1024

# RFC 959 §3.4.2 Block mode descriptor codes (bit flags in one descriptor byte).
BLOCK_HEADER_LEN = 3
BLOCK_FLAG_EOF = 0x40     # 64: end of data block is EOF
BLOCK_FLAG_EOR = 0x80     # 128: end of data block is EOR
BLOCK_FLAG_SUSPECT = 0x20  # 32: suspected errors in data block
BLOCK_FLAG_RESTART = 0x10  # 16: data block is a restart marker

# RFC 959 §3.4.3 Compressed mode primitives.
COMPRESSED_MAX_LITERAL = 127
COMPRESSED_MAX_RUN = 63
COMPRESSED_FILLER_BINARY = 0x00
COMPRESSED_FILLER_ASCII = 0x20
COMPRESSED_ESCAPE_BYTE = 0x00
COMPRESSED_DESCRIPTOR_EOF = BLOCK_FLAG_EOF  # 0x00 0x40 escape ends the file


class ModeCodecError(FilesystemOperationError):
    """A MODE frame is malformed; the transfer must fail atomically (426)."""

    def __init__(self, message: str) -> None:
        super().__init__("mode", 426, message)


def normalize_mode(mode: str | None) -> str:
    if mode is None:
        return MODE_STREAM
    normalized = str(mode).strip().upper()
    if normalized not in VALID_MODES:
        raise ModeCodecError(f"Unknown transfer mode: {mode!r}")
    return normalized


def normalize_transfer_type(transfer_type: str | None) -> str:
    """Return the supported FTP representation type (ASCII or Image)."""
    normalized = "I" if transfer_type is None else str(transfer_type).strip().upper()
    if normalized not in ("A", "I"):
        raise ModeCodecError(f"Unknown transfer type: {transfer_type!r}")
    return normalized


def compressed_filler_byte(transfer_type: str | None) -> int:
    return (
        COMPRESSED_FILLER_ASCII
        if normalize_transfer_type(transfer_type) == "A"
        else COMPRESSED_FILLER_BINARY
    )


# ---------------------------------------------------------------------------
# Stream mode — pass-through.
# ---------------------------------------------------------------------------

def stream_encode(chunks: Iterable[bytes]) -> Iterator[bytes]:
    yield from chunks


def stream_decode(chunks: Iterable[bytes]) -> Iterator[bytes]:
    yield from chunks


# ---------------------------------------------------------------------------
# Block mode — 1-byte descriptor + 2-byte big-endian byte count per block.
# ---------------------------------------------------------------------------

def _block_packet(payload: bytes, eof: bool) -> bytes:
    flags = BLOCK_FLAG_EOF if eof else 0
    return bytes([flags]) + struct.pack(">H", len(payload)) + payload


def block_encode(chunks: Iterable[bytes], block_size: int = WIRE_CHUNK_SIZE) -> Iterator[bytes]:
    if block_size < 1 or block_size > 0xFFFF:
        raise ModeCodecError("Invalid block size")
    source = iter(chunks)
    buffer = bytearray()
    while True:
        while len(buffer) <= block_size:
            try:
                buffer += next(source)
            except StopIteration:
                yield _block_packet(bytes(buffer), eof=True)
                return
        yield _block_packet(bytes(buffer[:block_size]), eof=False)
        del buffer[:block_size]


def block_decode(chunks: Iterable[bytes]) -> Iterator[bytes]:
    source = iter(chunks)
    buffer = bytearray()
    eof_seen = False

    def read(needed: int) -> bool:
        nonlocal buffer
        while len(buffer) < needed:
            try:
                buffer += next(source)
            except StopIteration:
                return False
        return True

    while True:
        if not read(BLOCK_HEADER_LEN):
            if eof_seen and not buffer:
                return
            raise ModeCodecError("Truncated block header; missing EOF")
        descriptor = buffer[0]
        count = struct.unpack(">H", bytes(buffer[1:3]))[0]
        del buffer[:BLOCK_HEADER_LEN]

        if not read(count):
            raise ModeCodecError("Truncated block payload; missing EOF")
        payload = bytes(buffer[:count])
        del buffer[:count]

        if descriptor & BLOCK_FLAG_EOF:
            eof_seen = True
        yield payload
        if eof_seen:
            if buffer:
                raise ModeCodecError("Data received after EOF block")
            try:
                extra = next(source)
            except StopIteration:
                return
            raise ModeCodecError(f"Data received after EOF block ({len(extra)} bytes)")


# ---------------------------------------------------------------------------
# Compressed mode — FTP run-length encoding (RFC 959 §3.4.3).
#   literal run    0nnnnnnn d(1) ... d(n)
#   repeated byte  10nnnnnn d            (byte d repeated n times)
#   filler         11nnnnnn              (n filler bytes, 0x00 for Image type)
#   escape         00 40                 (EOF)
# ---------------------------------------------------------------------------

def compressed_encode(
    chunks: Iterable[bytes], transfer_type: str | None = "I"
) -> Iterator[bytes]:
    source = iter(chunks)
    buffer = bytearray()
    filler_byte = compressed_filler_byte(transfer_type)

    def fill(needed: int) -> bool:
        nonlocal buffer
        while len(buffer) < needed:
            try:
                buffer += next(source)
            except StopIteration:
                return False
        return True

    while True:
        if not fill(1):
            break
        byte = buffer[0]

        run = 1
        while run < COMPRESSED_MAX_RUN and run < len(buffer) and buffer[run] == byte:
            run += 1
        if run < COMPRESSED_MAX_RUN and run == len(buffer):
            if fill(run + 1):
                while run < COMPRESSED_MAX_RUN and run < len(buffer) and buffer[run] == byte:
                    run += 1

        if run >= 2:
            del buffer[:run]
            if byte == filler_byte:
                yield bytes([0xC0 | run])
            else:
                yield bytes([0x80 | run, byte])
            continue

        fill(COMPRESSED_MAX_LITERAL + 2)
        count = 1
        while count < COMPRESSED_MAX_LITERAL and count + 1 < len(buffer):
            if buffer[count] == buffer[count + 1]:
                break
            count += 1
        literal = bytes(buffer[:count])
        del buffer[:count]
        yield bytes([count]) + literal

    yield bytes([COMPRESSED_ESCAPE_BYTE, COMPRESSED_DESCRIPTOR_EOF])


def compressed_decode(
    chunks: Iterable[bytes], transfer_type: str | None = "I"
) -> Iterator[bytes]:
    source = iter(chunks)
    buffer = bytearray()
    eof_seen = False
    filler_byte = compressed_filler_byte(transfer_type)

    def fill(needed: int) -> bool:
        nonlocal buffer
        while len(buffer) < needed:
            try:
                buffer += next(source)
            except StopIteration:
                return False
        return True

    while True:
        if not fill(1):
            break
        header = buffer[0]
        del buffer[0]

        if header & 0x80 == 0:
            count = header & 0x7F
            if count == 0:
                if not fill(1):
                    raise ModeCodecError("Truncated compressed escape; missing descriptor")
                descriptor = buffer[0]
                del buffer[0]
                if descriptor == 0 or descriptor & 0x0F:
                    raise ModeCodecError("Invalid compressed control byte")
                if descriptor & BLOCK_FLAG_EOF:
                    if eof_seen:
                        raise ModeCodecError("Duplicate EOF escape")
                    eof_seen = True
                    if fill(1):
                        raise ModeCodecError("Data received after EOF escape")
                    return
                continue
            if not fill(count):
                raise ModeCodecError("Truncated compressed literal run")
            payload = bytes(buffer[:count])
            del buffer[:count]
            yield payload
        elif header & 0x40:
            count = header & 0x3F
            if count == 0:
                raise ModeCodecError("Invalid zero-length filler run")
            yield bytes([filler_byte]) * count
        else:
            count = header & 0x3F
            if count == 0:
                raise ModeCodecError("Invalid zero-length repeated byte run")
            if not fill(1):
                raise ModeCodecError("Truncated compressed repeated byte")
            data = buffer[0]
            del buffer[0]
            yield bytes([data]) * count

    if eof_seen:
        return
    raise ModeCodecError("Missing EOF escape in compressed stream")


def _batch_wire(primitives: Iterable[bytes], size: int = WIRE_CHUNK_SIZE) -> Iterator[bytes]:
    buffer = bytearray()
    for primitive in primitives:
        buffer += primitive
        while len(buffer) >= size:
            yield bytes(buffer[:size])
            del buffer[:size]
    if buffer:
        yield bytes(buffer)


# ---------------------------------------------------------------------------
# Dispatchers used by the transfer boundary (server and client).
# ---------------------------------------------------------------------------

def encode_chunks(
    chunks: Iterable[bytes], mode: str | None, transfer_type: str | None = "I"
) -> Iterator[bytes]:
    normalized = normalize_mode(mode)
    if normalized == MODE_STREAM:
        yield from chunks
    elif normalized == MODE_BLOCK:
        yield from _batch_wire(block_encode(chunks))
    else:
        yield from _batch_wire(compressed_encode(chunks, transfer_type))


def decode_chunks(
    chunks: Iterable[bytes], mode: str | None, transfer_type: str | None = "I"
) -> Iterator[bytes]:
    normalized = normalize_mode(mode)
    if normalized == MODE_STREAM:
        yield from chunks
    elif normalized == MODE_BLOCK:
        yield from block_decode(chunks)
    else:
        yield from compressed_decode(chunks, transfer_type)
