from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from typing import Callable

from common.RDTHeader import RDTHeader


DEFAULT_TIMEOUT_S: float = 1.0
DEFAULT_MAX_TIMEOUTS: int = 10   # 10 × 1 s inactivity → hủy

# B-08: buffer đủ cho header (20) + payload tối đa (1024) + slack
_RECV_BUF: int = RDTHeader.size + 1024 + 64  # = 1108 bytes

ProgressCallback = Callable[[str, int, int | None], None]



class RDTReceiverAdapter:
    """Wraps receive_chunks_rdt như một TransferManager-compatible RDT receiver.

    Usage::

        adapter = RDTReceiverAdapter()
        manager = TransferManager(filesystem, receiver=adapter)

    TransferManager calls::

        adapter.receive(data_socket, endpoint, context) -> Iterable[bytes]
    """

    def receive(
        self,
        data_socket: socket.socket,
        endpoint: object,   
        context: object,    
    ) -> Iterator[bytes]:
        """Nhận chunks qua RDT, trả về generator để FilesystemService.store dùng."""
        transfer_id_hint: int | None = _ctx_transfer_id(context)
        timeout_s: float = getattr(context, "timeout_seconds", DEFAULT_TIMEOUT_S)

        max_timeouts: int = int(getattr(context, "max_timeouts", DEFAULT_MAX_TIMEOUTS))
        cancel_event: threading.Event | None = getattr(context, "cancel_event", None)

        return receive_chunks_rdt(
            data_socket,
            transfer_id_hint=transfer_id_hint,
            timeout_s=timeout_s,
            max_timeouts=max_timeouts,
            cancel_event=cancel_event,
        )

def receive_chunks_rdt(
    udp_socket: socket.socket,
    transfer_id_hint: int | None = None,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_timeouts: int = DEFAULT_MAX_TIMEOUTS,
    progress_cb: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> Iterator[bytes]:
    """Yield payload chunks từ Stop-and-Wait RDT sender.

    Caller (FilesystemService.store) chịu trách nhiệm ghi và commit atomic.

    Raises:
        RuntimeError: ABORT, cancel, hoặc inactivity timeout.
    """
    if cancel_event is None:
        cancel_event = threading.Event()

    udp_socket.settimeout(timeout_s)
    expected_seq = 0
    peer_addr: tuple | None = None
    transfer_id: int | None = transfer_id_hint
    timeout_count = 0
    committed_bytes = 0
    total_bytes: int | None = None   

    while True:
        if cancel_event.is_set():
            raise RuntimeError("Transfer cancelled by caller")

        try:
            data, addr = udp_socket.recvfrom(_RECV_BUF)
            timeout_count = 0
        except socket.timeout:
            timeout_count += 1
            if timeout_count >= max_timeouts:
                raise RuntimeError(
                    f"[RDT] Không nhận gói sau {max_timeouts * timeout_s:.0f}s. Hủy."
                )
            continue
        except OSError as exc:
            raise RuntimeError(f"[RDT] Socket error: {exc}") from exc

      
        if len(data) < RDTHeader.size:
            continue

        if peer_addr is not None and addr != peer_addr:
            print(f"[RDT][Security] Gói từ {addr}, mong {peer_addr}. Bỏ qua.")
            continue

        try:
            header = RDTHeader.deserialize(data)
        except ValueError:
            continue

        if transfer_id is None:
            transfer_id = header.transfer_id
        elif header.transfer_id != transfer_id:
            print(
                f"[RDT][Security] transfer_id {header.transfer_id}"
                f" != {transfer_id}. Bỏ qua."
            )
            continue

        if header.flags & RDTHeader.FLAG_ABORT:
            print("[RDT][Abort] Nhận tín hiệu hủy từ sender.")
            raise RuntimeError("Transfer aborted by sender")

        if header.flags & RDTHeader.FLAG_START:
            start_payload = data[RDTHeader.size: RDTHeader.size + header.length]
            if not header.verify_checksum(start_payload):
                print("[RDT][START] Checksum START lỗi. Bỏ qua.")
                continue

            if peer_addr is None:
                peer_addr = addr

            if len(start_payload) >= 8 and total_bytes is None:
                import struct as _struct
                try:
                    (raw_size,) = _struct.unpack_from("!Q", start_payload)
                    if raw_size > 0:
                        total_bytes = raw_size
                        print(f"[RDT][Start] File size: {total_bytes} bytes")
                except Exception:
                    pass
            continue  

        if not header.validate_length(data):
            print(
                f"[RDT][Length] header.length={header.length} "
                f"vượt quá dữ liệu thật ({len(data) - RDTHeader.size} bytes). Bỏ qua."
            )
            continue
        payload = data[RDTHeader.size: RDTHeader.size + header.length]

        if not header.verify_checksum(payload):
            print(f"[RDT][Checksum] Lỗi checksum seq={header.seq_num}. Bỏ qua.")
            continue

        if peer_addr is None:
            peer_addr = addr

        if header.seq_num == expected_seq:
            yield payload
            expected_seq += 1
            committed_bytes += len(payload)

            _send_ack(udp_socket, peer_addr, transfer_id, header.seq_num)

            if progress_cb:
                progress_cb(str(transfer_id), committed_bytes, total_bytes)

            if header.flags & RDTHeader.FLAG_FIN:
                _fin_grace(udp_socket, peer_addr, transfer_id, header.seq_num, timeout_s)
                return

        elif header.seq_num < expected_seq:
            print(f"[RDT][Dup] Gói cũ seq={header.seq_num}, re-ACK.")
            _send_ack(udp_socket, peer_addr, transfer_id, header.seq_num)

        else:
            print(
                f"[RDT][OOO] seq={header.seq_num} nhưng đợi seq={expected_seq}. Bỏ qua."
            )

def receive_file_rdt(
    udp_socket: socket.socket,
    save_path: str,
    progress_cb=None,
    is_cancelled=None,
) -> bool:
    """Legacy API giữ cho tests hiện có chạy được.

    Production code nên dùng :class:`RDTReceiverAdapter` + TransferManager.
    Socket KHÔNG đóng tại đây — caller (test/thread) chịu trách nhiệm close.
    """
    import os
    from common.file_handler import write_file_from_chunks

    cancel_event: threading.Event
    if is_cancelled is not None:
        class _PollEvent(threading.Event):
            def is_set(self) -> bool:  # type: ignore[override]
                return bool(is_cancelled())
        cancel_event = _PollEvent()
    else:
        cancel_event = threading.Event()

    adapted_cb: ProgressCallback | None = None
    if progress_cb is not None:
        def adapted_cb(tid: str, committed: int, total: int | None) -> None:
            progress_cb(committed)

    try:
        chunks_gen = receive_chunks_rdt(
            udp_socket,
            progress_cb=adapted_cb,
            cancel_event=cancel_event,
        )
        write_file_from_chunks(save_path, chunks_gen)
        return True
    except RuntimeError as exc:
        print(f"[RDT] {exc}")
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
        except OSError:
            pass
        return False

def _send_ack(
    sock: socket.socket,
    peer: tuple,
    transfer_id: int,
    ack_seq: int,
) -> None:
    hdr = RDTHeader(
        transfer_id=transfer_id,
        seq_num=0,
        ack_num=ack_seq,
        flags=RDTHeader.FLAG_ACK,
        length=0,
    )
    hdr.checksum = hdr.compute_checksum(b"")
    try:
        sock.sendto(hdr.serialize(), peer)
    except OSError:
        pass


def _fin_grace(
    sock: socket.socket,
    peer: tuple,
    transfer_id: int,
    fin_seq: int,
    timeout_s: float,
    grace_attempts: int = 3,
) -> None:
  
    sock.settimeout(timeout_s)
    for _ in range(grace_attempts):
        try:
            data, addr = sock.recvfrom(_RECV_BUF)
            if addr != peer or len(data) < RDTHeader.size:
                continue
            try:
                hdr = RDTHeader.deserialize(data)
            except ValueError:
                continue
            if (
                hdr.transfer_id == transfer_id
                and hdr.seq_num == fin_seq
                and (hdr.flags & RDTHeader.FLAG_FIN)
            ):
                _send_ack(sock, peer, transfer_id, fin_seq)
        except socket.timeout:
            continue  
        except OSError:
            break  
def _ctx_transfer_id(context: object) -> int | None:
    """Lấy transfer_id số nguyên từ TransferContext (có thể là str UUID)."""
    raw = getattr(context, "transfer_id", None)
    if raw is None:
        return None
    if isinstance(raw, str):
        import hashlib
        return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)
    return int(raw) & 0xFFFFFFFF