from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from typing import Callable

from common.RDTHeader import RDTHeader
from common.rdt_context import normalize_transfer_id


DEFAULT_TIMEOUT_S: float = 1.0
# Keep receiver failure bounded when the sender disappears.  Five one-second
# waits are long enough for normal retransmission but short enough for callers
# to observe a finite failure promptly.
DEFAULT_MAX_TIMEOUTS: int = 5
_RECV_BUF: int = RDTHeader.size + 1024 + 64 

ProgressCallback = Callable[[str, int, int | None], None]



class RDTReceiverAdapter:
    def receive(
        self,
        data_socket: socket.socket,
        endpoint: object,   
        context: object,    
    ) -> Iterator[bytes]:
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
                    f"[RDT] No packet received after {max_timeouts * timeout_s:.0f}s"
                )
            continue
        except OSError as exc:
            raise RuntimeError(f"[RDT] Socket error: {exc}") from exc

      
        if len(data) < RDTHeader.size:
            continue

        if peer_addr is not None and addr != peer_addr:
            print(f"[RDT][Security] Packet from {addr} ignored")
            continue

        try:
            header = RDTHeader.deserialize(data)
        except ValueError:
            continue

        if transfer_id is None:
            transfer_id = header.transfer_id
        elif header.transfer_id != transfer_id:
            print(f"[RDT][Security] transfer_id {header.transfer_id} != {transfer_id}")
            continue

        if header.flags & RDTHeader.FLAG_ABORT:
            if not header.verify_checksum(b""):
                continue
            print("[RDT][Abort] Sender cancelled transfer")
            raise RuntimeError("Transfer aborted by sender")

        if header.flags & RDTHeader.FLAG_START:
            if header.flags != RDTHeader.FLAG_START or header.seq_num != 0:
                continue
            start_payload = data[RDTHeader.size: RDTHeader.size + header.length]
            if not header.validate_length(data):
                continue
            if not header.verify_checksum(start_payload):
                print("[RDT][START] Invalid checksum")
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
            # START is idempotent.  ACK it every time so sender retries are safe.
            _send_ack(udp_socket, peer_addr, transfer_id, 0)
            continue

        if not header.validate_length(data):
            print(f"[RDT][Length] Invalid payload length seq={header.seq_num}")
            continue
        if not RDTHeader.is_valid_flags(header.flags):
            continue
        payload = data[RDTHeader.size: RDTHeader.size + header.length]

        if not header.verify_checksum(payload):
            print(f"[RDT][Checksum] Invalid checksum seq={header.seq_num}")
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
            print(f"[RDT][Dup] Duplicate seq={header.seq_num}, re-ACK")
            _send_ack(udp_socket, peer_addr, transfer_id, expected_seq - 1)

        else:
            print(f"[RDT][OOO] Got seq={header.seq_num}, expected={expected_seq}")
            # Go-Back-N uses a cumulative ACK for the last contiguous packet.
            if expected_seq > 0:
                _send_ack(udp_socket, peer_addr, transfer_id, expected_seq - 1)

def receive_file_rdt(
    udp_socket: socket.socket,
    save_path: str,
    progress_cb=None,
    is_cancelled=None,
    transfer_id: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> bool:
    import os
    from common.file_handler import write_file_from_chunks

    cancel_event: threading.Event
    if is_cancelled is not None:
        class _PollEvent(threading.Event):
            def is_set(self) -> bool:  
                return bool(is_cancelled())
        cancel_event = _PollEvent()
    else:
        cancel_event = threading.Event()

    adapted_cb: ProgressCallback | None = None
    if progress_cb is not None:
        def adapted_cb(tid: str, committed: int, total: int | None) -> None:
            progress_cb(committed)

    def combined_cb(tid: str, committed: int, total: int | None) -> None:
        if progress_callback is not None:
            progress_callback(tid, committed, total)
        if progress_cb is not None:
            progress_cb(committed)

    try:
        chunks_gen = receive_chunks_rdt(
            udp_socket,
            transfer_id_hint=transfer_id,
            progress_cb=combined_cb if (progress_callback or progress_cb) else None,
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
    """Return an integer transfer ID from a TransferContext (possibly a UUID string)."""
    raw = getattr(context, "transfer_id", None)
    if raw is None:
        return None
    return normalize_transfer_id(raw)
