"""Tests for the Role C transfer orchestration contract."""

import os
import threading

from common.filesystem_service import FilesystemService
from server.session import Session
from server.transfer_manager import TransferManager


class FakeSender:
    def __init__(self):
        self.payload = b""

    def send(self, chunks, data_socket, endpoint, cancel_event):
        for chunk in chunks:
            self.payload += chunk
        return len(self.payload)


class FakeReceiver:
    def receive(self, data_socket, endpoint, cancel_event):
        return iter((b"hello", b" ", b"world"))


def make_session(tmp_path):
    root = tmp_path / "ftp-root"
    root.mkdir()
    return root, Session(str(root))


def test_upload_uses_atomic_filesystem_store(tmp_path):
    root, session = make_session(tmp_path)
    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver())

    result = manager.upload(session, os.path.join(str(root), "hello.txt"), data_socket=object())

    assert result
    assert result.reply_code == 226
    assert result.bytes_transferred == 11
    assert (root / "hello.txt").read_bytes() == b"hello world"
    assert not list(root.glob("*.part"))


def test_download_reads_validated_file_and_calls_sender(tmp_path):
    root, session = make_session(tmp_path)
    (root / "hello.txt").write_bytes(b"hello world")
    sender = FakeSender()
    manager = TransferManager(FilesystemService(str(root)), sender=sender)

    result = manager.download(session, os.path.join(str(root), "hello.txt"), data_socket=object())

    assert result
    assert result.reply_code == 226
    assert sender.payload == b"hello world"


def test_cancel_sets_event_and_preserves_existing_file(tmp_path):
    root, session = make_session(tmp_path)
    target = root / "hello.txt"
    target.write_bytes(b"old")
    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver())
    cancelled = threading.Event()
    cancelled.set()

    result = manager.upload(session, str(target), chunks=(b"new",), cancel_event=cancelled)

    assert not result
    assert result.reply_code == 426
    assert target.read_bytes() == b"old"
    assert not list(root.glob("*.part"))
