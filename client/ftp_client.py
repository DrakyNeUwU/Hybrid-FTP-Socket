"""Small demo client for the Hybrid FTP TCP-control/UDP-RDT workflow."""

from __future__ import annotations

import os
import re
import socket
from collections.abc import Callable

from common.RDTHeader import RDTHeader
from common.rdt_context import normalize_transfer_id
from common.rdt_receiver import receive_file_rdt
from common.rdt_sender import send_file_rdt
from common.rdt_utils import format_port_command, parse_pasv_response


TransferProgressCallback = Callable[[str, str, int, int | None], None]


class FTPClient:
    def __init__(
        self,
        server_ip: str = "127.0.0.1",
        control_port: int = 2121,
        download_dir: str = "./client/downloads",
        progress_callback: TransferProgressCallback | None = None,
    ):
        self.server_ip = server_ip
        self.control_port = control_port
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.download_dir = download_dir
        self.progress_callback = progress_callback
        os.makedirs(self.download_dir, exist_ok=True)

    def connect(self) -> str:
        self.control_socket.connect((self.server_ip, self.control_port))
        return self._recv_reply()

    def login(self, username: str = "admin", password: str = "123456") -> None:
        self.command(f"USER {username}")
        reply = self.command(f"PASS {password}")
        if not reply.startswith("230"):
            raise RuntimeError(reply.strip())

    def close(self) -> None:
        try:
            self.command("QUIT")
        except OSError:
            pass
        self.control_socket.close()

    def command(self, value: str) -> str:
        self.control_socket.sendall(f"{value}\r\n".encode("utf-8"))
        return self._recv_reply()

    def enter_pasv(self) -> tuple[str, int]:
        reply = self.command("PASV")
        if not reply.startswith("227"):
            raise RuntimeError(reply.strip())
        return parse_pasv_response(reply)

    def enter_port(self) -> tuple[socket.socket, tuple[str, int]]:
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data_socket.bind(("0.0.0.0", 0))
        local_ip = self.control_socket.getsockname()[0]
        local_port = data_socket.getsockname()[1]
        reply = self.command(format_port_command(local_ip, local_port).strip())
        match = re.search(r"server UDP port (\d+)", reply)
        if not reply.startswith("200") or match is None:
            data_socket.close()
            raise RuntimeError(reply.strip())
        return data_socket, (self.server_ip, int(match.group(1)))

    def download_file(self, remote_filename: str, mode: str = "PASV") -> bool:
        if mode.upper() == "PASV":
            data_socket, endpoint = self._pasv_download_socket()
        else:
            data_socket, endpoint = self.enter_port()

        try:
            if mode.upper() == "ACTIVE":
                # Send before RETR as well: a server worker can begin immediately
                # after its 150 reply, while stateful firewalls need an outbound
                # datagram before accepting the server's first START.
                self._send_active_download_probe(data_socket, endpoint, 0)
            reply = self.command(f"RETR {remote_filename}")
            transfer_id = self._transfer_id_from_reply(reply)
            wire_transfer_id = normalize_transfer_id(transfer_id)
            if mode.upper() == "ACTIVE":
                # Open the client-to-server UDP path before the server sends START.
                # This is required by stateful firewalls/NATs for server-initiated
                # ACTIVE downloads; it does not carry file data or change FTP flow.
                self._send_active_download_probe(data_socket, endpoint, wire_transfer_id)
            destination = os.path.join(self.download_dir, os.path.basename(remote_filename))
            ok = receive_file_rdt(
                data_socket,
                destination,
                transfer_id=wire_transfer_id,
                progress_callback=lambda _tid, done, total: self._notify_progress(
                    "download", remote_filename, done, total
                ),
            )
            complete = self._recv_reply()
            return ok and complete.startswith("226")
        finally:
            data_socket.close()

    def upload_file(self, local_filepath: str, remote_filename: str,
                    cmd: str = "STOR", mode: str = "PASV") -> bool:
        if mode.upper() == "PASV":
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_socket.bind(("0.0.0.0", 0))
            endpoint = self.enter_pasv()
        else:
            data_socket, endpoint = self.enter_port()

        try:
            reply = self.command(f"{cmd} {remote_filename}")
            transfer_id = self._transfer_id_from_reply(reply)
            ok = send_file_rdt(
                local_filepath,
                endpoint[0],
                endpoint[1],
                transfer_id=normalize_transfer_id(transfer_id),
                udp_socket=data_socket,
                progress_cb=lambda done, total: self._notify_progress(
                    "upload", remote_filename, done, total
                ),
            )
            complete = self._recv_reply()
            return ok and complete.startswith("226")
        finally:
            data_socket.close()

    def upload_unique_file(self, local_filepath: str, mode: str = "PASV") -> bool:
        if mode.upper() == "PASV":
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_socket.bind(("0.0.0.0", 0))
            endpoint = self.enter_pasv()
        else:
            data_socket, endpoint = self.enter_port()
        try:
            reply = self.command("STOU")
            transfer_id = self._transfer_id_from_reply(reply)
            ok = send_file_rdt(
                local_filepath, endpoint[0], endpoint[1],
                transfer_id=normalize_transfer_id(transfer_id),
                udp_socket=data_socket,
            )
            return ok and self._recv_reply().startswith("226")
        finally:
            data_socket.close()

    def _pasv_download_socket(self) -> tuple[socket.socket, tuple[str, int]]:
        endpoint = self.enter_pasv()
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data_socket.bind(("0.0.0.0", 0))
        probe = RDTHeader(
            transfer_id=0,
            seq_num=0,
            ack_num=0,
            flags=RDTHeader.FLAG_START,
            length=0,
        )
        probe.checksum = probe.compute_checksum(b"")
        data_socket.sendto(probe.serialize(), endpoint)
        return data_socket, endpoint

    @staticmethod
    def _send_active_download_probe(
        data_socket: socket.socket,
        endpoint: tuple[str, int],
        transfer_id: int,
    ) -> None:
        """Create UDP state for an ACTIVE download without transferring data."""
        probe = RDTHeader(
            transfer_id=transfer_id,
            seq_num=0,
            ack_num=0,
            flags=RDTHeader.FLAG_START,
            length=0,
        )
        probe.checksum = probe.compute_checksum(b"")
        data_socket.sendto(probe.serialize(), endpoint)

    def _recv_reply(self) -> str:
        return self.control_socket.recv(4096).decode("utf-8")

    def _notify_progress(
        self, direction: str, filename: str, transferred: int, total: int | None
    ) -> None:
        if self.progress_callback is not None:
            self.progress_callback(direction, filename, transferred, total)

    @staticmethod
    def _transfer_id_from_reply(reply: str) -> str:
        match = re.search(r"transfer_id=([A-Za-z0-9_-]+)", reply)
        if not reply.startswith("150") or match is None:
            raise RuntimeError(reply.strip())
        return match.group(1)
