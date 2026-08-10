from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from typing import Callable

from common.RDTHeader import RDTHeader
from common.rdt_context import decode_start_metadata, normalize_transfer_id


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
        expected_mode: str = getattr(context, "transfer_mode", "S")
        expected_type: str = getattr(context, "transfer_type", "I")

        return receive_chunks_rdt(
            data_socket,
            transfer_id_hint=transfer_id_hint,
            timeout_s=timeout_s,
            max_timeouts=max_timeouts,
            cancel_event=cancel_event,
            expected_mode=expected_mode,
            expected_type=expected_type,
        )

def receive_chunks_rdt(
    udp_socket: socket.socket,
    transfer_id_hint: int | None = None,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_timeouts: int = DEFAULT_MAX_TIMEOUTS,
    progress_cb: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    expected_mode: str | None = None,
    expected_type: str | None = None,
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

            try:
                raw_size, wire_mode, wire_type = decode_start_metadata(start_payload)
            except ValueError as error:
                raise RuntimeError(f"[RDT] Invalid START metadata: {error}") from error
            if expected_mode is not None:
                if wire_mode is None or wire_mode != expected_mode:
                    raise RuntimeError(
                        f"[RDT] MODE mismatch: expected {expected_mode}, got {wire_mode or 'legacy'}"
                    )
            if expected_type is not None:
                if wire_type is None or wire_type != expected_type:
                    raise RuntimeError(
                        f"[RDT] TYPE mismatch: expected {expected_type}, got {wire_type or 'legacy'}"
                    )
            if total_bytes is None and raw_size > 0:
                total_bytes = raw_size
                print(f"[RDT][Start] File size: {total_bytes} bytes")
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
            expected_seq += 1
            committed_bytes += len(payload)

            _send_ack(udp_socket, peer_addr, transfer_id, header.seq_num)

            if progress_cb:
                progress_cb(str(transfer_id), committed_bytes, total_bytes)

            yield payload

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
    mode: str = "S",
    transfer_type: str = "I",
) -> bool:
    import os
    from common.file_handler import write_file_from_chunks_atomic
    from common.mode_codec import decode_chunks

    cancel_event: threading.Event
    if is_cancelled is not None:
        class _PollEvent(threading.Event):
            def is_set(self) -> bool:  
                return bool(is_cancelled())
        cancel_event = _PollEvent()
    else:
        cancel_event = threading.Event()

    # The RDT layer reports wire (encoded) bytes; the public progress_callback
    # must count logical decoded bytes so a compressed transfer can reach 100%
    # and a block transfer never overshoots it.
    total_size: list[int | None] = [None]

    def _rdt_progress_cb(tid: str, committed: int, total: int | None) -> None:
        if total is not None:
            total_size[0] = total
        if progress_cb is not None:
            progress_cb(committed)

    def _counted(decoded_chunks):
        committed = 0
        for chunk in decoded_chunks:
            committed += len(chunk)
            if progress_callback is not None:
                progress_callback(str(transfer_id), committed, total_size[0])
            yield chunk

    try:
        chunks_gen = receive_chunks_rdt(
            udp_socket,
            transfer_id_hint=transfer_id,
            progress_cb=_rdt_progress_cb if (progress_callback or progress_cb) else None,
            cancel_event=cancel_event,
            expected_mode=mode,
            expected_type=transfer_type,
        )
        write_file_from_chunks_atomic(
            save_path,
            _counted(decode_chunks(chunks_gen, mode, transfer_type)),
        )
        return True
    except RuntimeError as exc:
        print(f"[RDT] {exc}")
        return False
    except Exception as exc:
        print(f"[MODE] {exc}")
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
