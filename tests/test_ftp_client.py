"""Control framing and client-side failure tests for the production FTP client."""

from __future__ import annotations

import os
from unittest.mock import patch

from client.ftp_client import FTPClient
from common.rdt_receiver import receive_file_rdt


class ScriptedSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, _size):
        return self.chunks.pop(0) if self.chunks else b""


def make_client(tmp_path, chunks) -> FTPClient:
    client = FTPClient(download_dir=str(tmp_path))
    client.control_socket.close()
    client.control_socket = ScriptedSocket(chunks)
    return client


def test_split_reply_is_reassembled(tmp_path):
    client = make_client(tmp_path, [b"200 Mode", b" Block\r\n"])
    assert client.command("MODE B") == "200 Mode Block\r\n"
    assert client.transfer_mode == "B"
    assert client._negotiated_mode == "B"


def test_coalesced_replies_remain_buffered(tmp_path):
    client = make_client(tmp_path, [b"200 Type set to Binary\r\n200 Mode Stream\r\n"])
    assert client.command("TYPE I").startswith("200")
    assert client.command("MODE S") == "200 Mode Stream\r\n"
    assert client.transfer_type == "I"
    assert client.transfer_mode == "S"


def test_multiline_and_listing_replies(tmp_path):
    client = make_client(
        tmp_path,
        [
            b"214-Supported commands:\r\n MODE TYPE\r\n214 Help OK\r\n",
            b"150 Listing\r\n-rw-r--r-- file.bin\r\n226 Done\r\n",
        ],
    )
    help_reply = client.command("HELP")
    listing = client.command("LIST")
    assert help_reply.endswith("214 Help OK\r\n")
    assert "file.bin" in listing
    assert listing.endswith("226 Done\r\n")


def test_failed_mode_does_not_change_local_state(tmp_path):
    client = make_client(tmp_path, [b"501 Invalid MODE\r\n"])
    client.transfer_mode = "S"
    assert client.command("MODE X").startswith("501")
    assert client.transfer_mode == "S"


def test_malformed_download_preserves_existing_destination(tmp_path):
    destination = tmp_path / "existing.bin"
    destination.write_bytes(b"OLD")
    malformed = iter((b"\x40\x00\x05ab",))
    with patch("common.rdt_receiver.receive_chunks_rdt", return_value=malformed):
        assert not receive_file_rdt(object(), str(destination), transfer_id=1, mode="B")
    assert destination.read_bytes() == b"OLD"
    assert not [name for name in os.listdir(tmp_path) if name.endswith(".part")]
