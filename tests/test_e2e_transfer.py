"""End-to-end localhost tests for TCP control plus UDP/RDT file transfer."""

from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest

from client.ftp_client import FTPClient
from common.file_handler import compute_hash, read_file_bytes, write_file
from common.rdt_context import normalize_transfer_id
from common.rdt_sender import send_file_rdt
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

    def test_pasv_mode_matrix_preserves_sha256(self):
        """S/B/C all round-trip through PASV with identical SHA-256."""
        source = os.path.join(self.temp_dir.name, "mode-source.bin")
        payload = bytes(range(256)) * 16 + b"\x00\xff\x40\x41" * 64 + b"mode" * 200
        write_file(source, payload)

        for mode in ("S", "B", "C"):
            with self.subTest(mode=mode):
                client = FTPClient(
                    "127.0.0.1", self.server.port,
                    os.path.join(self.temp_dir.name, f"dl-pasv-{mode}"),
                    transfer_mode=mode,
                )
                try:
                    self.assertTrue(client.connect().startswith("220"))
                    client.login()
                    self.assertTrue(client.upload_file(source, f"remote-{mode}.bin", mode="PASV"))
                    remote = os.path.join(self.root, f"remote-{mode}.bin")
                    self.assertEqual(compute_hash(source), compute_hash(remote))
                    self.assertTrue(client.download_file(f"remote-{mode}.bin", mode="PASV"))
                    downloaded = os.path.join(client.download_dir, f"remote-{mode}.bin")
                    self.assertEqual(compute_hash(source), compute_hash(downloaded))
                finally:
                    client.close()

    def test_active_mode_matrix_preserves_sha256(self):
        """S/B/C all round-trip through ACTIVE with identical SHA-256."""
        source = os.path.join(self.temp_dir.name, "active-mode-source.bin")
        payload = b"active-mode\x00\xff" + bytes(range(255)) * 6 + b"B" * 500
        write_file(source, payload)

        for mode in ("S", "B", "C"):
            with self.subTest(mode=mode):
                client = FTPClient(
                    "127.0.0.1", self.server.port,
                    os.path.join(self.temp_dir.name, f"dl-active-{mode}"),
                    transfer_mode=mode,
                )
                try:
                    self.assertTrue(client.connect().startswith("220"))
                    client.login()
                    self.assertTrue(client.upload_file(source, f"active-{mode}.bin", mode="ACTIVE"))
                    remote = os.path.join(self.root, f"active-{mode}.bin")
                    self.assertEqual(compute_hash(source), compute_hash(remote))
                    self.assertTrue(client.download_file(f"active-{mode}.bin", mode="ACTIVE"))
                    downloaded = os.path.join(client.download_dir, f"active-{mode}.bin")
                    self.assertEqual(compute_hash(source), compute_hash(downloaded))
                finally:
                    client.close()

    def test_block_mode_stou_appe(self):
        """STOU and APPE use the block codec on the production path."""
        mode = "B"
        addition = os.path.join(self.temp_dir.name, "block-add.bin")
        write_file(addition, b"block-append-" * 300)

        self.assertTrue(self.client.set_mode("B").startswith("200"))
        self.assertTrue(self.client.upload_file(addition, "block-append.bin", cmd="APPE", mode="PASV"))
        target = os.path.join(self.root, "block-append.bin")
        self.assertEqual(read_file_bytes(target), read_file_bytes(addition))

        client = FTPClient("127.0.0.1", self.server.port, transfer_mode=mode)
        try:
            self.assertTrue(client.connect().startswith("220"))
            client.login()
            before = set(os.listdir(self.root))
            self.assertTrue(client.upload_unique_file(addition, mode="PASV"))
            created = set(os.listdir(self.root)) - before
            self.assertEqual(len(created), 1)
            unique_path = os.path.join(self.root, created.pop())
            self.assertEqual(compute_hash(addition), compute_hash(unique_path))
        finally:
            client.close()

    def test_start_metadata_mode_mismatch_fails_without_publishing(self):
        """A sender using S after MODE B must get 426, never silent corruption."""
        source = os.path.join(self.temp_dir.name, "crafted-stream.bin")
        write_file(source, b"\x40\x00\x03abc")
        self.assertTrue(self.client.set_mode("B").startswith("200"))
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data_socket.bind(("0.0.0.0", 0))
        endpoint = self.client.enter_pasv()
        try:
            preliminary = self.client.command("STOR mismatch.bin")
            transfer_id = self.client._transfer_id_from_reply(preliminary)
            self.assertFalse(
                send_file_rdt(
                    source,
                    endpoint[0],
                    endpoint[1],
                    transfer_id=normalize_transfer_id(transfer_id),
                    udp_socket=data_socket,
                    mode="S",
                    transfer_type="I",
                )
            )
            final_reply = self.client._recv_reply()
            self.assertTrue(final_reply.startswith("426"), final_reply)
            self.assertFalse(os.path.exists(os.path.join(self.root, "mismatch.bin")))
            self.assertFalse(self._temporary_files("mismatch.bin"))
        finally:
            data_socket.close()

    def test_mode_progress_counts_logical_bytes(self):
        """B/C progress never exceeds the logical size and reaches it exactly."""
        source = os.path.join(self.temp_dir.name, "progress-mode.bin")
        payload = b"\x00compressible\x00" * 2000 + bytes(range(256)) * 8
        write_file(source, payload)

        for mode in ("B", "C"):
            with self.subTest(mode=mode):
                events: list[tuple[str, str, int, int | None]] = []
                client = FTPClient(
                    "127.0.0.1", self.server.port,
                    transfer_mode=mode,
                    progress_callback=lambda *event: events.append(event),
                )
                try:
                    self.assertTrue(client.connect().startswith("220"))
                    client.login()
                    self.assertTrue(client.upload_file(source, f"progress-{mode}.bin", mode="PASV"))
                    self.assertEqual(
                        compute_hash(source),
                        compute_hash(os.path.join(self.root, f"progress-{mode}.bin")),
                    )
                    uploads = [e for e in events if e[0] == "upload"]
                    self.assertTrue(uploads)
                    for _direction, _name, done, total in uploads:
                        self.assertEqual(total, len(payload))
                        self.assertLessEqual(done, total)
                    self.assertEqual(uploads[-1][2], len(payload))

                    events.clear()
                    self.assertTrue(client.download_file(f"progress-{mode}.bin", mode="PASV"))
                    downloads = [e for e in events if e[0] == "download"]
                    self.assertTrue(downloads)
                    for _direction, _name, done, total in downloads:
                        self.assertEqual(total, len(payload))
                        self.assertLessEqual(done, total)
                    self.assertEqual(downloads[-1][2], len(payload))
                finally:
                    client.close()

    def test_two_clients_different_modes_do_not_mix(self):
        """Concurrent B and C sessions keep independent mode and payload state."""
        mode_b_source = os.path.join(self.temp_dir.name, "mode-b.bin")
        mode_c_source = os.path.join(self.temp_dir.name, "mode-c.bin")
        payload_b = b"B-mode-" * 3000 + bytes(range(128))
        payload_c = (b"\x00" * 64) * 200 + b"C-mode-" * 3000
        write_file(mode_b_source, payload_b)
        write_file(mode_c_source, payload_c)

        clients = [
            FTPClient("127.0.0.1", self.server.port, transfer_mode="B"),
            FTPClient("127.0.0.1", self.server.port, transfer_mode="C"),
        ]
        sources = [(mode_b_source, "mode-b.bin"), (mode_c_source, "mode-c.bin")]
        for client in clients:
            self.assertTrue(client.connect().startswith("220"))
            client.login()

        errors = []
        errors_lock = threading.Lock()

        def worker(client, source, remote):
            try:
                if not client.upload_file(source, remote, mode="PASV"):
                    raise RuntimeError("upload failed")
                if not client.download_file(remote, mode="PASV"):
                    raise RuntimeError("download failed")
                downloaded = os.path.join(client.download_dir, remote)
                if compute_hash(source) != compute_hash(downloaded):
                    raise RuntimeError("SHA-256 mismatch")
            except Exception as exc:
                with errors_lock:
                    errors.append(str(exc))
            finally:
                client.close()

        workers = [
            threading.Thread(target=worker, args=(client, source, remote), daemon=True)
            for client, (source, remote) in zip(clients, sources)
        ]
        for worker_thread in workers:
            worker_thread.start()
        for worker_thread in workers:
            worker_thread.join(timeout=20)
            self.assertFalse(worker_thread.is_alive(), "mode worker did not finish")

        self.assertEqual(errors, [])
        self.assertEqual(compute_hash(mode_b_source), compute_hash(os.path.join(self.root, "mode-b.bin")))
        self.assertEqual(compute_hash(mode_c_source), compute_hash(os.path.join(self.root, "mode-c.bin")))

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

    def test_server_stop_during_mode_b_upload_cleanup(self):
        """Stopping the server mid-B-transfer cancels the worker and removes .part."""
        source = os.path.join(self.temp_dir.name, "stop-b-src.bin")
        write_file(source, os.urandom(1024 * 4096) + b"B-mode-stop" * 1000)
        client = FTPClient(
            "127.0.0.1", self.server.port,
            os.path.join(self.temp_dir.name, "stop-b-dl"),
            transfer_mode="B",
        )
        self.assertTrue(client.connect().startswith("220"))
        client.login()

        worker = threading.Thread(
            target=client.upload_file, args=(source, "stop-b.bin"),
            kwargs={"mode": "PASV"}, daemon=True,
        )
        worker.start()
        self._wait_until(lambda: bool(self._temporary_files("stop-b.bin")), timeout=5.0)

        self.server.stop()
        self.thread.join(timeout=3)
        worker.join(timeout=8)
        self.assertFalse(worker.is_alive(), "upload worker did not finish after server stop")
        self._wait_until(lambda: not self._temporary_files("stop-b.bin"))
        self.assertNotIn("stop-b.bin", os.listdir(self.root))
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
