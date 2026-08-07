"""RDT Sender and Receiver Adapters for TransferManager.

Role A provides these adapters so TransferManager can send and receive file chunks
via RDT datagrams over UDP sockets.
"""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterable

from common.RDTHeader import RDTHeader


class RDTReceiverAdapter:
    """Adapter for receiving RDT UDP datagrams into bytes chunks."""

    def __init__(self, timeout: float = 0.5) -> None:
        self.timeout = timeout

    def receive(
        self,
        data_socket: socket.socket | None,
        endpoint: tuple[str, int] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> list[bytes]:
        if data_socket is None:
            raise ValueError("Data socket is required for receive")

        data_socket.settimeout(self.timeout)
        expected_seq = 0
        chunks: list[bytes] = []

        while True:
            if cancel_event and cancel_event.is_set():
                break
            try:
                data, addr = data_socket.recvfrom(2048)
                if len(data) < RDTHeader.size:
                    continue
                header = RDTHeader.deserialize(data)
                if header.flags & RDTHeader.FLAG_ABORT:
                    break

                payload = data[RDTHeader.size : RDTHeader.size + header.length]
                if not header.verify_checksum(payload):
                    continue

                # Send ACK
                ack_header = RDTHeader(
                    seq_num=0,
                    ack_num=header.seq_num,
                    flags=RDTHeader.FLAG_ACK,
                    length=0,
                )
                ack_header.checksum = ack_header.compute_checksum(b"")
                try:
                    data_socket.sendto(ack_header.serialize(), addr)
                except OSError:
                    pass

                if header.seq_num == expected_seq:
                    chunks.append(payload)
                    expected_seq += 1
                    if header.flags & RDTHeader.FLAG_FIN:
                        break
            except socket.timeout:
                continue
            except OSError:
                break

        return chunks


class RDTSenderAdapter:
    """Adapter for sending bytes chunks via RDT UDP datagrams."""

    def __init__(self, timeout: float = 0.5, max_retries: int = 10) -> None:
        self.timeout = timeout
        self.max_retries = max_retries

    def send(
        self,
        chunks: Iterable[bytes],
        data_socket: socket.socket | None,
        endpoint: tuple[str, int] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> int | bool:
        if data_socket is None:
            raise ValueError("Data socket is required for send")
        if endpoint is None:
            raise ValueError("Endpoint (ip, port) is required for send")

        data_socket.settimeout(self.timeout)
        dest_ip, dest_port = endpoint
        chunk_list = list(chunks)
        if not chunk_list:
            chunk_list = [b""]

        transferred_bytes = 0
        for seq_num, chunk in enumerate(chunk_list):
            if cancel_event and cancel_event.is_set():
                abort_header = RDTHeader(
                    seq_num=seq_num, ack_num=0, flags=RDTHeader.FLAG_ABORT, length=0
                )
                abort_header.checksum = abort_header.compute_checksum(b"")
                try:
                    data_socket.sendto(abort_header.serialize(), (dest_ip, dest_port))
                except OSError:
                    pass
                return False

            is_last = seq_num == len(chunk_list) - 1
            flags = RDTHeader.FLAG_FIN if is_last else RDTHeader.FLAG_DATA

            header = RDTHeader(
                seq_num=seq_num, ack_num=0, flags=flags, length=len(chunk)
            )
            header.checksum = header.compute_checksum(chunk)
            packet = header.serialize() + chunk

            retries = 0
            ack_received = False
            while retries < self.max_retries:
                if cancel_event and cancel_event.is_set():
                    return False
                try:
                    data_socket.sendto(packet, (dest_ip, dest_port))
                    ack_data, _ = data_socket.recvfrom(1024)
                    if len(ack_data) >= RDTHeader.size:
                        ack_header = RDTHeader.deserialize(ack_data)
                        if (
                            ack_header.flags & RDTHeader.FLAG_ACK
                        ) and ack_header.ack_num == seq_num:
                            ack_received = True
                            transferred_bytes += len(chunk)
                            break
                except socket.timeout:
                    retries += 1
                except OSError:
                    return False

            if not ack_received:
                return False

        return transferred_bytes
