"""Tests for the Role C transfer orchestration contract."""

import os
import threading

from common.filesystem_service import FilesystemService
from common.mode_codec import decode_chunks, encode_chunks
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
    def __init__(self, payload=b"hello world"):
        self.payload = payload

    def receive(self, data_socket, endpoint, cancel_event):
        return iter((self.payload,))


def make_session(tmp_path, mode="S"):
    root = tmp_path / "ftp-root"
    root.mkdir()
    session = Session(str(root))
    session.transfer_mode = mode
    return root, session


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
    assert result.bytes_transferred == len(b"hello world")


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


def test_cancel_mid_block_stream_preserves_old_file(tmp_path):
    """ABOR mid-block stream: decoder/store stop promptly, no partial commit."""
    root, session = make_session(tmp_path, mode="B")
    target = root / "mid.bin"
    target.write_bytes(b"old-content")
    encoded = b"".join(encode_chunks((os.urandom(2048) for _ in range(40)), "B"))
    cancelled = threading.Event()

    def mid_stream():
        pieces = [encoded[i:i + 256] for i in range(0, len(encoded), 256)]
        for index, piece in enumerate(pieces):
            if index == 20:
                cancelled.set()
            yield piece

    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver())

    result = manager.upload(session, os.path.join(str(root), "mid.bin"),
                            chunks=mid_stream(), cancel_event=cancelled)

    assert not result
    assert result.reply_code == 426
    assert target.read_bytes() == b"old-content"
    assert not list(root.glob("*.part"))


def test_disconnect_mid_compressed_stream_preserves_old_file(tmp_path):
    """TCP/UDP disconnect mid-stream: finite 426, old file kept, no .part."""
    root, session = make_session(tmp_path, mode="C")
    target = root / "disc.bin"
    target.write_bytes(b"old-content")
    encoded = b"".join(encode_chunks((os.urandom(1024) for _ in range(60)), "C"))

    def stream_then_error():
        pieces = [encoded[i:i + 300] for i in range(0, len(encoded), 300)]
        yield from pieces
        raise RuntimeError("connection reset by peer")

    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver())

    result = manager.upload(session, os.path.join(str(root), "disc.bin"),
                            chunks=stream_then_error())

    assert not result
    assert result.reply_code == 426
    assert target.read_bytes() == b"old-content"
    assert not list(root.glob("*.part"))


def test_upload_decodes_block_mode_before_store(tmp_path):
    payload = bytes(range(256)) * 8
    root, session = make_session(tmp_path, mode="B")
    encoded = b"".join(encode_chunks((payload[i:i + 257] for i in range(0, len(payload), 257)), "B"))
    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver(encoded))

    result = manager.upload(session, os.path.join(str(root), "block.bin"), data_socket=object())

    assert result
    assert result.reply_code == 226
    assert (root / "block.bin").read_bytes() == payload
    assert not list(root.glob("*.part"))


def test_upload_decodes_compressed_mode_before_store(tmp_path):
    payload = b"compress-me-" * 4000 + b"\x00" * 200
    root, session = make_session(tmp_path, mode="C")
    encoded = b"".join(encode_chunks((payload[i:i + 1000] for i in range(0, len(payload), 1000)), "C"))
    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver(encoded))

    result = manager.upload(session, os.path.join(str(root), "comp.bin"), data_socket=object())

    assert result
    assert result.reply_code == 226
    assert (root / "comp.bin").read_bytes() == payload
    assert not list(root.glob("*.part"))


def test_download_encodes_mode_b_on_the_wire(tmp_path):
    payload = b"wire-encoded-please" * 300
    root, session = make_session(tmp_path, mode="B")
    (root / "block.bin").write_bytes(payload)
    sender = FakeSender()
    manager = TransferManager(FilesystemService(str(root)), sender=sender)

    result = manager.download(session, os.path.join(str(root), "block.bin"), data_socket=object())

    assert result
    assert result.reply_code == 226
    assert sender.payload != payload
    assert b"".join(decode_chunks((sender.payload,), "B")) == payload
    assert result.bytes_transferred == len(payload)


def test_download_encodes_mode_c_on_the_wire(tmp_path):
    payload = b"AAAA" * 3000 + bytes(range(128)) * 4
    root, session = make_session(tmp_path, mode="C")
    (root / "comp.bin").write_bytes(payload)
    sender = FakeSender()
    manager = TransferManager(FilesystemService(str(root)), sender=sender)

    result = manager.download(session, os.path.join(str(root), "comp.bin"), data_socket=object())

    assert result
    assert result.reply_code == 226
    assert b"".join(decode_chunks((sender.payload,), "C")) == payload
    assert result.bytes_transferred == len(payload)


def test_malformed_mode_stream_fails_atomic_426(tmp_path):
    root, session = make_session(tmp_path, mode="B")
    target = root / "bad.bin"
    target.write_bytes(b"old-content")
    truncated = b"\x40\x00\x05ab"  # block header claims 5 bytes, has 2
    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver(truncated))

    result = manager.upload(session, os.path.join(str(root), "bad.bin"), data_socket=object())

    assert not result
    assert result.reply_code == 426
    assert target.read_bytes() == b"old-content"
    assert not list(root.glob("*.part"))


def test_append_decodes_within_shared_lock_boundary(tmp_path):
    payload = b"appended-" * 500
    root, session = make_session(tmp_path, mode="B")
    target = root / "append.bin"
    target.write_bytes(b"base-")
    encoded = b"".join(encode_chunks((payload[i:i + 511] for i in range(0, len(payload), 511)), "B"))
    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver(encoded))

    result = manager.append(session, os.path.join(str(root), "append.bin"), data_socket=object())

    assert result
    assert result.reply_code == 226
    assert target.read_bytes() == b"base-" + payload
    assert not list(root.glob("*.part"))


def test_stou_decodes_before_publish(tmp_path):
    payload = b"unique-" * 1000 + b"\x00" * 64
    root, session = make_session(tmp_path, mode="C")
    encoded = b"".join(encode_chunks((payload[i:i + 333] for i in range(0, len(payload), 333)), "C"))
    manager = TransferManager(FilesystemService(str(root)), receiver=FakeReceiver(encoded))

    result = manager.upload_unique(session, data_socket=object())

    assert result
    assert result.reply_code == 226
    files = list(root.glob("upload_*.bin"))
    assert len(files) == 1
    assert files[0].read_bytes() == payload
    assert not list(root.glob("*.part"))
