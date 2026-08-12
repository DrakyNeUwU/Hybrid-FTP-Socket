"""Small demo client for the Hybrid FTP TCP-control/UDP-RDT workflow."""

from __future__ import annotations

import os
import re
import socket
from typing import Callable
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
        transfer_mode: str = "S",
        transfer_type: str = "I",
    ):
        self.server_ip = server_ip
        self.control_port = control_port
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.download_dir = download_dir
        self.progress_callback = progress_callback
        self.transfer_mode = transfer_mode.upper()
        self.transfer_type = transfer_type.upper()
        self._negotiated_mode = None
        self._negotiated_type = None
        self._reply_buffer = bytearray()
        if self.transfer_mode not in ("S", "B", "C"):
            raise ValueError(f"Unsupported transfer mode: {transfer_mode!r}")
        if self.transfer_type not in ("A", "I"):
            raise ValueError(f"Unsupported transfer type: {transfer_type!r}")
        os.makedirs(self.download_dir, exist_ok=True)

    def connect(self) -> str:
        self.control_socket.connect((self.server_ip, self.control_port))
        return self._recv_reply()

    def login(self, username: str, password: str) -> None:
        reply = self.command(f"USER {username}")
        if not reply.startswith("331"):
            raise RuntimeError(reply.strip())
        reply = self.command(f"PASS {password}")
        if not reply.startswith("230"):
            raise RuntimeError(reply.strip())

    def close(self) -> None:
        try:
            self.command("QUIT")
        except (OSError, ConnectionError):
            pass
        self.control_socket.close()

    def command(self, value: str) -> str:
        self.control_socket.sendall(f"{value}\r\n".encode("utf-8"))
        command_name = value.strip().split(maxsplit=1)[0].upper() if value.strip() else ""
        if command_name in ("LIST", "NLST"):
            reply = self._recv_listing_reply()
        else:
            reply = self._recv_reply()
        self._record_successful_negotiation(value, reply)
        return reply

    def set_mode(self, mode: str) -> str:
        """Negotiate a transfer mode; the local mode only changes after a 200."""
        normalized = mode.upper()
        if normalized not in ("S", "B", "C"):
            raise ValueError(f"Unsupported transfer mode: {mode!r}")
        reply = self.command(f"MODE {normalized}")
        if reply.startswith("200"):
            self.transfer_mode = normalized
            self._negotiated_mode = normalized
        return reply

    def set_type(self, transfer_type: str) -> str:
        """Negotiate ASCII/Image representation after a successful 200 reply."""
        normalized = transfer_type.upper()
        if normalized not in ("A", "I"):
            raise ValueError(f"Unsupported transfer type: {transfer_type!r}")
        return self.command(f"TYPE {normalized}")

    def _ensure_transfer_type(self) -> None:
        if self._negotiated_type == self.transfer_type:
            return
        reply = self.command(f"TYPE {self.transfer_type}")
        if not reply.startswith("200"):
            raise RuntimeError(reply.strip())

    def _ensure_transfer_mode(self) -> None:
        if self._negotiated_mode == self.transfer_mode:
            return
        reply = self.command(f"MODE {self.transfer_mode}")
        if not reply.startswith("200"):
            raise RuntimeError(reply.strip())
        self._negotiated_mode = self.transfer_mode

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

    def download_file(
        self,
        remote_filename: str,
        mode: str = "PASV",
        reply_callback: Callable[[str], None] | None = None,
    ) -> bool:
        self._ensure_transfer_type()
        self._ensure_transfer_mode()
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
            if reply_callback:
                reply_callback(reply.strip())
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
                mode=self.transfer_mode,
                transfer_type=self.transfer_type,
                progress_callback=lambda _tid, done, total: self._notify_progress(
                    "download", remote_filename, done, total
                ),
            )
            complete = self._recv_reply()
            return ok and complete.startswith("226")
        finally:
            data_socket.close()

    def upload_file(
        self,
        local_filepath: str,
        remote_filename: str,
        cmd: str = "STOR",
        mode: str = "PASV",
        reply_callback: Callable[[str], None] | None = None,
    ) -> bool:
        self._ensure_transfer_type()
        self._ensure_transfer_mode()
        if mode.upper() == "PASV":
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_socket.bind(("0.0.0.0", 0))
            endpoint = self.enter_pasv()
        else:
            data_socket, endpoint = self.enter_port()

        try:
            reply = self.command(f"{cmd} {remote_filename}")
            if reply_callback:
                reply_callback(reply.strip())
            transfer_id = self._transfer_id_from_reply(reply)
            ok = send_file_rdt(
                local_filepath,
                endpoint[0],
                endpoint[1],
                transfer_id=normalize_transfer_id(transfer_id),
                udp_socket=data_socket,
                mode=self.transfer_mode,
                transfer_type=self.transfer_type,
                progress_cb=lambda done, total: self._notify_progress(
                    "upload", remote_filename, done, total
                ),
            )
            complete = self._recv_reply()
            return ok and complete.startswith("226")
        finally:
            data_socket.close()

    def upload_unique_file(
        self,
        local_filepath: str,
        mode: str = "PASV",
        reply_callback: Callable[[str], None] | None = None,
    ) -> bool:
        self._ensure_transfer_type()
        self._ensure_transfer_mode()
        if mode.upper() == "PASV":
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_socket.bind(("0.0.0.0", 0))
            endpoint = self.enter_pasv()
        else:
            data_socket, endpoint = self.enter_port()
        try:
            reply = self.command("STOU")
            if reply_callback:
                reply_callback(reply.strip())
            transfer_id = self._transfer_id_from_reply(reply)
            ok = send_file_rdt(
                local_filepath, endpoint[0], endpoint[1],
                transfer_id=normalize_transfer_id(transfer_id),
                udp_socket=data_socket,
                mode=self.transfer_mode,
                transfer_type=self.transfer_type,
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
        first = self._recv_line()
        lines = [first]
        if len(first) >= 4 and first[:3].isdigit() and first[3:4] == b"-":
            terminal = first[:3] + b" "
            while True:
                line = self._recv_line()
                lines.append(line)
                if line.startswith(terminal):
                    break
        return b"".join(lines).decode("utf-8")

    def _recv_listing_reply(self) -> str:
        first = self._recv_line()
        lines = [first]
        if not first.startswith(b"150"):
            return first.decode("utf-8")
        while True:
            line = self._recv_line()
            lines.append(line)
            if len(line) >= 3 and line[:3] in (b"226", b"425", b"426", b"450", b"550"):
                break
        return b"".join(lines).decode("utf-8")

    def _recv_line(self) -> bytes:
        while b"\r\n" not in self._reply_buffer:
            chunk = self.control_socket.recv(4096)
            if not chunk:
                raise ConnectionError("Control connection closed before complete FTP reply")
            self._reply_buffer.extend(chunk)
        line, remainder = self._reply_buffer.split(b"\r\n", 1)
        self._reply_buffer = bytearray(remainder)
        return bytes(line) + b"\r\n"

    def _record_successful_negotiation(self, value: str, reply: str) -> None:
        if not reply.startswith("200"):
            return
        parts = value.strip().split()
        if len(parts) != 2:
            return
        command_name, argument = parts[0].upper(), parts[1].upper()
        if command_name == "MODE" and argument in ("S", "B", "C"):
            self.transfer_mode = argument
            self._negotiated_mode = argument
        elif command_name == "TYPE" and argument in ("A", "I"):
            self.transfer_type = argument
            self._negotiated_type = argument

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
