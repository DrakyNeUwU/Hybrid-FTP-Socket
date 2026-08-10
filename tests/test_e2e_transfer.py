"""End-to-end localhost tests for TCP control plus UDP/RDT file transfer."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest

from client.ftp_client import FTPClient
from common.file_handler import compute_hash, read_file_bytes, write_file
from server.threaded_server import FTPServer


class TestEndToEndPasvTransfer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.temp_dir.name, "ftp-root")
        self.server = FTPServer(host="127.0.0.1", port=0, ftp_root=self.root)
        self.thread = threading.Thread(target=self.server.start, daemon=True)
        self.thread.start()
        deadline = time.time() + 3
        while self.server.port == 0 and time.time() < deadline:
            time.sleep(0.02)
        self.assertNotEqual(self.server.port, 0)
        self.progress_events: list[tuple[str, str, int, int | None]] = []
        self.client = FTPClient(
            "127.0.0.1",
            self.server.port,
            progress_callback=lambda *event: self.progress_events.append(event),
        )
        self.assertTrue(self.client.connect().startswith("220"))
        self.client.login()

    def tearDown(self):
        try:
            self.client.close()
        except (AttributeError, OSError):
            pass
        self.server.stop()
        self.thread.join(timeout=3)
        self.temp_dir.cleanup()

    def test_pasv_upload_then_download_preserves_sha256(self):
        source = os.path.join(self.temp_dir.name, "source.bin")
        payload = bytes(range(256)) * 8 + b"hybrid-ftp\x00\xff"
        write_file(source, payload)

        self.assertTrue(self.client.upload_file(source, "remote.bin", mode="PASV"))
        remote = os.path.join(self.root, "remote.bin")
        self.assertTrue(os.path.exists(remote))
        self.assertEqual(compute_hash(source), compute_hash(remote))

        self.assertTrue(self.client.download_file("remote.bin", mode="PASV"))
        downloaded = os.path.join(self.client.download_dir, "remote.bin")
        self.assertEqual(compute_hash(source), compute_hash(downloaded))
        self.assertEqual({event[0] for event in self.progress_events}, {"upload", "download"})
        self.assertTrue(all(event[2] > 0 for event in self.progress_events))
        download_events = [event for event in self.progress_events if event[0] == "download"]
        self.assertTrue(all(event[3] == len(payload) for event in download_events))

    def test_active_upload_then_download_preserves_sha256(self):
        source = os.path.join(self.temp_dir.name, "active-source.bin")
        payload = b"active-mode\x00" + bytes(range(255)) * 4
        write_file(source, payload)

        self.assertTrue(self.client.upload_file(source, "active.bin", mode="ACTIVE"))
        remote = os.path.join(self.root, "active.bin")
        self.assertEqual(compute_hash(source), compute_hash(remote))

        self.assertTrue(self.client.download_file("active.bin", mode="ACTIVE"))
        downloaded = os.path.join(self.client.download_dir, "active.bin")
        self.assertEqual(compute_hash(source), compute_hash(downloaded))

    def test_pasv_stou_appe_hash_and_type_lifecycle(self):
        """Role C transfer lifecycle covers unique store, atomic append and HASH."""
        initial = os.path.join(self.temp_dir.name, "initial.txt")
        addition = os.path.join(self.temp_dir.name, "addition.txt")
        unique = os.path.join(self.temp_dir.name, "unique.bin")
        write_file(initial, b"first-")
        write_file(addition, b"second")
        write_file(unique, bytes(range(32)))

        self.assertTrue(self.client.command("TYPE I").startswith("200"))
        self.assertTrue(self.client.upload_file(initial, "append-target.txt", mode="PASV"))
        self.assertTrue(
            self.client.upload_file(addition, "append-target.txt", cmd="APPE", mode="PASV")
        )
        remote = os.path.join(self.root, "append-target.txt")
        self.assertEqual(read_file_bytes(remote), b"first-second")
        self.assertEqual(
            self.client.command("HASH append-target.txt").strip(),
            f"213 SHA256 {compute_hash(remote)}",
        )
        self.assertTrue(self.client.command("TYPE A").startswith("200"))

        before = set(os.listdir(self.root))
        self.assertTrue(self.client.upload_unique_file(unique, mode="PASV"))
        created = set(os.listdir(self.root)) - before
        self.assertEqual(len(created), 1)
        unique_path = os.path.join(self.root, created.pop())
        self.assertEqual(compute_hash(unique), compute_hash(unique_path))

    def test_three_pasv_clients_transfer_independently(self):
        """Three sessions transfer in parallel without mixing file contents."""
        client_count = 3
        ready = threading.Barrier(client_count + 1)
        start_transfers = threading.Event()
        errors: list[str] = []
        errors_lock = threading.Lock()
        sources: list[tuple[str, str, str]] = []

        for client_id in range(client_count):
            source = os.path.join(self.temp_dir.name, f"client-{client_id}.bin")
            remote = f"concurrent-{client_id}.bin"
            payload = (f"client-{client_id}-".encode("ascii") + bytes([client_id])) * 8192
            write_file(source, payload)
            sources.append((source, remote, os.path.join(self.temp_dir.name, f"downloads-{client_id}")))

        def worker(source: str, remote: str, download_dir: str) -> None:
            client = FTPClient("127.0.0.1", self.server.port, download_dir)
            try:
                if not client.connect().startswith("220"):
                    raise RuntimeError("server banner was not 220")
                client.login()
                ready.wait(timeout=5)
                if not start_transfers.wait(timeout=5):
                    raise RuntimeError("transfer start signal timed out")
                if not client.upload_file(source, remote, mode="PASV"):
                    raise RuntimeError("upload failed")
                if not client.download_file(remote, mode="PASV"):
                    raise RuntimeError("download failed")
                downloaded = os.path.join(download_dir, remote)
                if compute_hash(source) != compute_hash(downloaded):
                    raise RuntimeError("download SHA-256 mismatch")
            except (OSError, RuntimeError, threading.BrokenBarrierError) as exc:
                with errors_lock:
                    errors.append(str(exc))
            finally:
                client.close()

        workers = [
            threading.Thread(target=worker, args=source, daemon=True)
            for source in sources
        ]
        for thread in workers:
            thread.start()

        ready.wait(timeout=5)
        self.assertEqual(self.server.get_active_client_count(), client_count + 1)
        start_transfers.set()
        for thread in workers:
            thread.join(timeout=20)
            self.assertFalse(thread.is_alive(), "concurrent client did not finish")

        self.assertEqual(errors, [])
        for source, remote, download_dir in sources:
            self.assertEqual(compute_hash(source), compute_hash(os.path.join(self.root, remote)))
            self.assertEqual(compute_hash(source), compute_hash(os.path.join(download_dir, remote)))

    def test_two_clients_append_same_file_without_lost_update(self):
        remote_name = "shared-append.bin"
        remote_path = os.path.join(self.root, remote_name)
        base = b"base-"
        first_payload = b"A" * (16 * 1024)
        second_payload = b"B" * (16 * 1024)
        write_file(remote_path, base)

        first_source = os.path.join(self.temp_dir.name, "append-a.bin")
        second_source = os.path.join(self.temp_dir.name, "append-b.bin")
        write_file(first_source, first_payload)
        write_file(second_source, second_payload)

        clients = [
            FTPClient("127.0.0.1", self.server.port),
            FTPClient("127.0.0.1", self.server.port),
        ]
        sources = [first_source, second_source]
        barrier = threading.Barrier(3)
        results = []
        results_lock = threading.Lock()

        for client in clients:
            self.assertTrue(client.connect().startswith("220"))
            client.login()

        def append_worker(client, source):
            try:
                barrier.wait(timeout=5)
                result = client.upload_file(
                    source, remote_name, cmd="APPE", mode="PASV"
                )
                with results_lock:
                    results.append(result)
            finally:
                client.close()

        workers = [
            threading.Thread(target=append_worker, args=pair, daemon=True)
            for pair in zip(clients, sources)
        ]
        for worker in workers:
            worker.start()
        barrier.wait(timeout=5)
        for worker in workers:
            worker.join(timeout=15)
            self.assertFalse(worker.is_alive(), "concurrent APPE did not finish")

        self.assertEqual(results, [True, True])
        final = read_file_bytes(remote_path)
        self.assertIn(
            final,
            (
                base + first_payload + second_payload,
                base + second_payload + first_payload,
            ),
        )

    def test_abor_waiting_upload_removes_temporary_file(self):
        """ABOR cancels a real PASV upload waiting for UDP data."""
        target = os.path.join(self.root, "abort-target.bin")
        write_file(target, b"old-content")

        self.client.enter_pasv()
        reply = self.client.command("STOR abort-target.bin")
        self.assertTrue(reply.startswith("150"))
        self._wait_until(lambda: bool(self._temporary_files("abort-target.bin")))

        replies = self._send_and_collect(self.client, "ABOR", "226 Abort successful")
        self.assertIn("226 Abort successful", replies)
        self._wait_until(lambda: not self._temporary_files("abort-target.bin"))
        self.assertEqual(read_file_bytes(target), b"old-content")
        self.assertTrue(self.client.command("NOOP").startswith("200"))

    def test_disconnect_waiting_upload_removes_temporary_file(self):
        """Control disconnect cancels a real PASV upload and keeps old data."""
        target = os.path.join(self.root, "disconnect-target.bin")
        write_file(target, b"old-content")
        client = FTPClient("127.0.0.1", self.server.port, os.path.join(self.temp_dir.name, "disconnect-downloads"))
        try:
            self.assertTrue(client.connect().startswith("220"))
            client.login()
            client.enter_pasv()
            self.assertTrue(client.command("STOR disconnect-target.bin").startswith("150"))
            self._wait_until(lambda: bool(self._temporary_files("disconnect-target.bin")))

            client.control_socket.close()
            self._wait_until(lambda: not self._temporary_files("disconnect-target.bin"))
            self._wait_until(lambda: self.server.get_active_client_count() == 1)
            self.assertEqual(read_file_bytes(target), b"old-content")
        finally:
            try:
                client.control_socket.close()
            except OSError:
                pass

    def _temporary_files(self, basename: str) -> list[str]:
        prefix = f".{basename}."
        return [
            name for name in os.listdir(self.root)
            if name.startswith(prefix) and name.endswith(".part")
        ]

    def _wait_until(self, condition, timeout: float = 3.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return
            time.sleep(0.02)
        self.fail("condition did not become true before timeout")

    @staticmethod
    def _send_and_collect(client: FTPClient, command: str, expected: str) -> str:
        client.control_socket.sendall(f"{command}\r\n".encode("utf-8"))
        original_timeout = client.control_socket.gettimeout()
        client.control_socket.settimeout(0.2)
        replies = ""
        deadline = time.time() + 3
        try:
            while time.time() < deadline and expected not in replies:
                try:
                    replies += client.control_socket.recv(4096).decode("utf-8")
                except TimeoutError:
                    continue
        finally:
            client.control_socket.settimeout(original_timeout)
        return replies


if __name__ == "__main__":
    unittest.main()
