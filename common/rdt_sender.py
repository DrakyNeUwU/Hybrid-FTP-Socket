from __future__ import annotations

import socket
import threading
from collections.abc import Iterable, Iterator
from typing import Callable

from common.RDTHeader import RDTHeader

DEFAULT_TIMEOUT_S: float = 0.5
DEFAULT_RETRY_LIMIT: int = 10
DEFAULT_CHUNK_SIZE: int = 1024

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
) -> int:
    if cancel_event is None:
        cancel_event = threading.Event()
    _own_socket = udp_socket is None
    if _own_socket:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp_socket.settimeout(timeout_s)
    resolved_ip = socket.gethostbyname(dest_ip)
    transferred_bytes = 0

    try:
        _send_start(udp_socket, transfer_id, total_bytes, resolved_ip, dest_port)
        for seq_num, (chunk, is_last) in enumerate(_lookahead(chunks)):
            if cancel_event.is_set():
                _send_abort(udp_socket, transfer_id, seq_num, resolved_ip, dest_port)
                raise RuntimeError("Transfer cancelled by caller")

            flags = RDTHeader.FLAG_FIN if is_last else RDTHeader.FLAG_DATA
            header = RDTHeader(
                transfer_id=transfer_id,
                seq_num=seq_num,
                ack_num=0,
                flags=flags,
                length=len(chunk),
            )
            header.checksum = header.compute_checksum(chunk)
            packet = header.serialize() + chunk

            ack_received = False
            for attempt in range(1, retry_limit + 1):
                if cancel_event.is_set():
                    _send_abort(udp_socket, transfer_id, seq_num, resolved_ip, dest_port)
                    raise RuntimeError("Transfer cancelled during retransmit")

                try:
                    udp_socket.sendto(packet, (resolved_ip, dest_port))
                    ack_data, addr = udp_socket.recvfrom(RDTHeader.size + 64)
                    if addr[0] != resolved_ip or addr[1] != dest_port:
                        print(
                            f"[RDT][Security] ACK từ {addr}, "
                            f"mong {(resolved_ip, dest_port)}. Bỏ qua."
                        )
                        continue

                    try:
                        ack_hdr = RDTHeader.deserialize(ack_data)
                    except ValueError:
                        continue

                    if not ack_hdr.verify_checksum(b""):
                        print(
                            f"[RDT][Security] ACK checksum lỗi seq={seq_num}. Bỏ qua."
                        )
                        continue
                    if ack_hdr.length != 0:
                        print(
                            f"[RDT][Security] ACK length={ack_hdr.length} != 0. Bỏ qua."
                        )
                        continue
                    if (
                        (ack_hdr.flags & RDTHeader.FLAG_ACK)
                        and ack_hdr.transfer_id == transfer_id
                        and ack_hdr.ack_num == seq_num
                    ):
                        ack_received = True
                        transferred_bytes += len(chunk)
                        if progress_cb:
                            progress_cb(str(transfer_id), transferred_bytes, total_bytes)
                        break

                except socket.timeout:
                    print(
                        f"[RDT][Timeout] Gửi lại seq={seq_num} "
                        f"(lần {attempt}/{retry_limit})"
                    )

            if not ack_received:
                raise RuntimeError(
                    f"[RDT] Quá {retry_limit} lần thử gói seq={seq_num}. Hủy."
                )

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
) -> bool:
    import random
    import os
    from common.file_handler import read_file_chunks

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

    adapted_cb: ProgressCallback | None = None
    if progress_cb is not None:
        def adapted_cb(tid: str, acked: int, total: int | None) -> None:
            progress_cb(acked, total)

    try:
        send_chunks_rdt(
            read_file_chunks(filepath),
            dest_ip,
            dest_port,
            transfer_id,
            retry_limit=max_retries,
            progress_cb=adapted_cb,
            cancel_event=cancel_event,
            total_bytes=total_size,
        )
        return True
    except RuntimeError as exc:
        print(f"[RDT] {exc}")
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
) -> None:
    import struct as _struct
    size_payload = _struct.pack("!Q", total_bytes if total_bytes is not None else 0)
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


def _ctx_transfer_id(context: object) -> int:
    import random
    raw = getattr(context, "transfer_id", None)
    if raw is None:
        return random.randint(1, 0xFFFFFFFF)
    if isinstance(raw, str):
        import hashlib
        return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)
    return int(raw) & 0xFFFFFFFF