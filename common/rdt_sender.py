from __future__ import annotations

import socket
import threading
from collections.abc import Iterable, Iterator
from typing import Callable

from common.RDTHeader import RDTHeader
from common.rdt_context import encode_start_metadata, normalize_transfer_id

DEFAULT_TIMEOUT_S: float = 0.5
DEFAULT_RETRY_LIMIT: int = 10
DEFAULT_CHUNK_SIZE: int = 1024
DEFAULT_WINDOW_SIZE: int = 4

ProgressCallback = Callable[[str, int, int | None], None]

class RDTSenderAdapter:

    def send(
        self,
        chunks: Iterable[bytes],
        data_socket: socket.socket,
        endpoint: object,  
        context: object,  
    ) -> int:
        host: str = getattr(endpoint, "host", "127.0.0.1")
        port: int = getattr(endpoint, "port", 0)
        transfer_id: int = _ctx_transfer_id(context)
        timeout_s: float = getattr(context, "timeout_seconds", DEFAULT_TIMEOUT_S)
        retry_limit: int = getattr(context, "retry_limit", DEFAULT_RETRY_LIMIT)
        cancel_event: threading.Event | None = getattr(context, "cancel_event", None)
        total_bytes: int | None = getattr(context, "total_bytes", None)
        window_size: int = int(getattr(context, "window_size", DEFAULT_WINDOW_SIZE))
        transfer_mode: str = getattr(context, "transfer_mode", "S")
        transfer_type: str = getattr(context, "transfer_type", "I")

        try:
            return send_chunks_rdt(
                chunks,
                host,
                port,
                transfer_id,
                udp_socket=data_socket,   
                timeout_s=timeout_s,
                retry_limit=retry_limit,
                cancel_event=cancel_event,
                total_bytes=total_bytes,
                window_size=window_size,
                transfer_mode=transfer_mode,
                transfer_type=transfer_type,
            )
        except RuntimeError as exc:
            raise RuntimeError(str(exc)) from exc

def send_chunks_rdt(
    chunks: Iterable[bytes],
    dest_ip: str,
    dest_port: int,
    transfer_id: int,
    *,
    udp_socket: socket.socket | None = None,   
    timeout_s: float = DEFAULT_TIMEOUT_S,
    retry_limit: int = DEFAULT_RETRY_LIMIT,
    progress_cb: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    total_bytes: int | None = None,
    window_size: int = DEFAULT_WINDOW_SIZE,
    transfer_mode: str = "S",
    transfer_type: str = "I",
) -> int:
    """Send chunks with a bounded Go-Back-N window.

    The wire header is unchanged.  ACK numbers are cumulative: an ACK for N
    confirms every DATA/FIN sequence through N.  ``START`` is acknowledged
    before the data window opens, so a receiver never silently misses metadata.
    """
    if window_size < 1:
        raise ValueError("window_size must be at least 1")
    if cancel_event is None:
        cancel_event = threading.Event()
    _own_socket = udp_socket is None
    if _own_socket:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp_socket.settimeout(timeout_s)
    resolved_ip = socket.gethostbyname(dest_ip)
    transferred_bytes = 0

    try:
        _send_start_with_ack(
            udp_socket, transfer_id, total_bytes, resolved_ip, dest_port,
            retry_limit, cancel_event,
            transfer_mode, transfer_type,
        )
        pending = enumerate(_lookahead(chunks))
        pending_exhausted = False
        window: dict[int, tuple[bytes, int]] = {}
        next_seq = 0
        last_acked = -1
        timeout_count = 0

        while not pending_exhausted or window:
            if cancel_event.is_set():
                _send_abort(udp_socket, transfer_id, next_seq, resolved_ip, dest_port)
                raise RuntimeError("Transfer cancelled by caller")

            while not pending_exhausted and len(window) < window_size:
                try:
                    seq_num, (chunk, is_last) = next(pending)
                except StopIteration:
                    pending_exhausted = True
                    break
                flags = RDTHeader.FLAG_FIN if is_last else RDTHeader.FLAG_DATA
                header = RDTHeader(transfer_id, seq_num, 0, flags, length=len(chunk))
                header.checksum = header.compute_checksum(chunk)
                window[seq_num] = (header.serialize() + chunk, len(chunk))
                udp_socket.sendto(window[seq_num][0], (resolved_ip, dest_port))
                next_seq = seq_num + 1

            try:
                ack_data, addr = udp_socket.recvfrom(RDTHeader.size + 64)
            except socket.timeout:
                timeout_count += 1
                if timeout_count >= retry_limit:
                    raise RuntimeError(
                        f"[RDT] Retry limit {retry_limit} exceeded for seq={last_acked + 1}"
                    )
                print(f"[RDT][Timeout] Go-Back-N retry ({timeout_count}/{retry_limit})")
                for packet, _ in window.values():
                    udp_socket.sendto(packet, (resolved_ip, dest_port))
                continue

            if addr[0] != resolved_ip or addr[1] != dest_port:
                print(f"[RDT][Security] ACK from {addr} ignored")
                continue
            try:
                ack_hdr = RDTHeader.deserialize(ack_data)
            except ValueError:
                continue
            if not _valid_ack(ack_hdr, transfer_id):
                continue
            if ack_hdr.ack_num <= last_acked or ack_hdr.ack_num >= next_seq:
                continue

            timeout_count = 0
            while window and min(window) <= ack_hdr.ack_num:
                seq_num = min(window)
                _, chunk_length = window.pop(seq_num)
                transferred_bytes += chunk_length
            last_acked = ack_hdr.ack_num
            if progress_cb:
                progress_cb(str(transfer_id), transferred_bytes, total_bytes)

        return transferred_bytes
    finally:
        if _own_socket:
            udp_socket.close()

def send_file_rdt(
    filepath: str,
    dest_ip: str,
    dest_port: int,
    progress_cb=None,
    is_cancelled=None,
    max_retries: int = DEFAULT_RETRY_LIMIT,
    transfer_id: int | None = None,
    udp_socket: socket.socket | None = None,
    mode: str = "S",
    transfer_type: str = "I",
) -> bool:
    import random
    import os
    from common.file_handler import read_file_chunks
    from common.mode_codec import encode_chunks

    if transfer_id is None:
        transfer_id = random.randint(1, 0xFFFFFFFF)

    cancel_event: threading.Event
    if is_cancelled is not None:
        class _PollEvent(threading.Event):
            def is_set(self) -> bool:  
                return bool(is_cancelled())
        cancel_event = _PollEvent()
    else:
        cancel_event = threading.Event()

    total_size = os.path.getsize(filepath) if os.path.exists(filepath) else None

    # The RDT layer acknowledges wire (encoded) bytes; the public progress_cb
    # must count logical file bytes so a compressed transfer can reach 100% and
    # a block transfer never overshoots it.
    def _counted(logical_chunks):
        committed = 0
        for chunk in logical_chunks:
            committed += len(chunk)
            if progress_cb is not None:
                progress_cb(committed, total_size)
            yield chunk

    try:
        send_chunks_rdt(
            encode_chunks(_counted(read_file_chunks(filepath)), mode, transfer_type),
            dest_ip,
            dest_port,
            transfer_id,
            udp_socket=udp_socket,
            retry_limit=max_retries,
            cancel_event=cancel_event,
            total_bytes=total_size,
            transfer_mode=mode,
            transfer_type=transfer_type,
        )
        return True
    except RuntimeError as exc:
        print(f"[RDT] {exc}")
        return False
    except Exception as exc:
        print(f"[MODE] {exc}")
        return False

def _lookahead(iterable: Iterable[bytes]) -> Iterator[tuple[bytes, bool]]:
    it = iter(iterable)
    try:
        current = next(it)
    except StopIteration:
        yield b"", True
        return
    for nxt in it:
        yield current, False
        current = nxt
    yield current, True


def _send_abort(
    sock: socket.socket,
    transfer_id: int,
    seq_num: int,
    dest_ip: str,      
    dest_port: int,
) -> None:
    try:
        hdr = RDTHeader(
            transfer_id=transfer_id,
            seq_num=seq_num,
            ack_num=0,
            flags=RDTHeader.FLAG_ABORT,
            length=0,
        )
        hdr.checksum = hdr.compute_checksum(b"")
        sock.sendto(hdr.serialize(), (dest_ip, dest_port))
    except OSError:
        pass


def _send_start(
    sock: socket.socket,
    transfer_id: int,
    total_bytes: int | None,
    dest_ip: str,
    dest_port: int,
    transfer_mode: str,
    transfer_type: str,
) -> None:
    size_payload = encode_start_metadata(total_bytes, transfer_mode, transfer_type)
    try:
        hdr = RDTHeader(
            transfer_id=transfer_id,
            seq_num=0,
            ack_num=0,
            flags=RDTHeader.FLAG_START,
            length=len(size_payload),
        )
        hdr.checksum = hdr.compute_checksum(size_payload)
        sock.sendto(hdr.serialize() + size_payload, (dest_ip, dest_port))
    except OSError:
        pass


def _send_start_with_ack(
    sock: socket.socket,
    transfer_id: int,
    total_bytes: int | None,
    dest_ip: str,
    dest_port: int,
    retry_limit: int,
    cancel_event: threading.Event,
    transfer_mode: str,
    transfer_type: str,
) -> None:
    """Send START until its ACK arrives or the bounded retry limit is reached."""
    for attempt in range(1, retry_limit + 1):
        if cancel_event.is_set():
            _send_abort(sock, transfer_id, 0, dest_ip, dest_port)
            raise RuntimeError("Transfer cancelled before START")
        _send_start(
            sock, transfer_id, total_bytes, dest_ip, dest_port,
            transfer_mode, transfer_type,
        )
        try:
            ack_data, addr = sock.recvfrom(RDTHeader.size + 64)
        except socket.timeout:
            print(f"[RDT][Timeout] START retry ({attempt}/{retry_limit})")
            continue
        if addr[0] != dest_ip or addr[1] != dest_port:
            continue
        try:
            ack_hdr = RDTHeader.deserialize(ack_data)
        except ValueError:
            continue
        if _valid_ack(ack_hdr, transfer_id) and ack_hdr.ack_num == 0:
            return
    raise RuntimeError(f"[RDT] START retry limit {retry_limit} exceeded")


def _valid_ack(header: RDTHeader, transfer_id: int) -> bool:
    return (
        header.verify_checksum(b"")
        and header.length == 0
        and RDTHeader.is_valid_flags(header.flags)
        and header.flags == RDTHeader.FLAG_ACK
        and header.transfer_id == transfer_id
        and header.seq_num == 0
    )


def _ctx_transfer_id(context: object) -> int:
    import random
    raw = getattr(context, "transfer_id", None)
    if raw is None:
        return random.randint(1, 0xFFFFFFFF)
    return normalize_transfer_id(raw)
