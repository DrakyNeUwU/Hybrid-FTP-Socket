import os
import random
import socket
import threading
import time
import unittest

from common.rdt_sender import send_file_rdt, RDTSenderAdapter
from common.rdt_receiver import receive_file_rdt, RDTReceiverAdapter
from common.file_handler import compute_hash, write_file, write_file_from_chunks, read_file_chunks

class NetworkProxy(threading.Thread):
    def __init__(
        self,
        target_port: int,
        drop_rate: float = 0.0,
        corrupt_rate: float = 0.0,
        drop_ack_rate: float = 0.0,
    ):
        super().__init__(daemon=True)
        self.target_port = target_port
        self.drop_rate = drop_rate
        self.corrupt_rate = corrupt_rate
        self.drop_ack_rate = drop_ack_rate
        self.running = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.listen_port = self.sock.getsockname()[1]  
        self.sock.settimeout(0.3)

        self._client_map: dict[int, tuple] = {}

    def run(self) -> None:
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            from_receiver = addr[1] == self.target_port
            if not from_receiver:
                self._client_map[addr[1]] = addr
                dest = ("127.0.0.1", self.target_port)
                if random.random() < self.drop_rate:
                    continue
            else:
                if not self._client_map:
                    continue
                dest = next(iter(self._client_map.values()))
                
                if random.random() < self.drop_ack_rate:
                    continue
               
                if random.random() < self.drop_rate:
                    continue

            if self.corrupt_rate > 0 and random.random() < self.corrupt_rate:
                if len(data) > 10:
                    ba = bytearray(data)
                    ba[-1] ^= 0xFF
                    data = bytes(ba)

            try:
                self.sock.sendto(data, dest)
            except OSError:
                break

    def stop(self) -> None:
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass

class _SimpleEndpoint:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.mode = "passive"

class _SimpleContext:
    def __init__(
        self,
        transfer_id: int,
        timeout_seconds: float = 0.5,
        retry_limit: int = 15,
        max_timeouts: int = 20,
    ):
        self.transfer_id = transfer_id
        self.timeout_seconds = timeout_seconds
        self.retry_limit = retry_limit
        self.max_timeouts = max_timeouts
        self.cancel_event = threading.Event()

def _run_transfer(
    src_path: str,
    dst_path: str,
    drop_rate: float = 0.0,
    corrupt_rate: float = 0.0,
    drop_ack_rate: float = 0.0,
    timeout: float = 20.0,
    retry_limit: int = 15,
) -> tuple[bool, bool]:
    rec_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rec_sock.bind(("127.0.0.1", 0))
    receiver_port = rec_sock.getsockname()[1]

    proxy: NetworkProxy | None = None
    actual_dest_port = receiver_port

    if drop_rate > 0 or corrupt_rate > 0 or drop_ack_rate > 0:
        proxy = NetworkProxy(
            target_port=receiver_port,
            drop_rate=drop_rate,
            corrupt_rate=corrupt_rate,
            drop_ack_rate=drop_ack_rate,
        )
        proxy.start()
        actual_dest_port = proxy.listen_port   

    recv_result: list[bool] = []

    def _recv():
        ok = receive_file_rdt(rec_sock, dst_path)
        recv_result.append(ok)

    rec_thread = threading.Thread(target=_recv, daemon=True)
    rec_thread.start()
    time.sleep(0.05)

    send_ok = send_file_rdt(
        src_path, "127.0.0.1", actual_dest_port,
        max_retries=retry_limit,
    )

    rec_thread.join(timeout=timeout)
    if proxy:
        proxy.stop()
    rec_sock.close()

    recv_ok = bool(recv_result and recv_result[0])
    return send_ok, recv_ok

def _run_transfer_adapter(
    src_path: str,
    dst_path: str,
    drop_rate: float = 0.0,
    corrupt_rate: float = 0.0,
    drop_ack_rate: float = 0.0,
    timeout: float = 20.0,
    retry_limit: int = 15,
) -> tuple[bool, bool]:
 
    transfer_id = random.randint(1, 0xFFFFFFFF)

    rec_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rec_sock.bind(("127.0.0.1", 0))
    receiver_port = rec_sock.getsockname()[1]

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.bind(("127.0.0.1", 0))

    proxy: NetworkProxy | None = None
    dest_port = receiver_port

    if drop_rate > 0 or corrupt_rate > 0 or drop_ack_rate > 0:
        proxy = NetworkProxy(
            target_port=receiver_port,
            drop_rate=drop_rate,
            corrupt_rate=corrupt_rate,
            drop_ack_rate=drop_ack_rate,
        )
        proxy.start()
        dest_port = proxy.listen_port

    endpoint = _SimpleEndpoint("127.0.0.1", dest_port)
    ctx_send = _SimpleContext(transfer_id, retry_limit=retry_limit)
    ctx_recv = _SimpleContext(transfer_id)

    recv_ok_flag: list[bool] = []
    recv_error: list[str] = []

    def _recv():
        try:       
            write_file_from_chunks(
                dst_path,
                RDTReceiverAdapter().receive(rec_sock, endpoint, ctx_recv),
            )
            recv_ok_flag.append(True)
        except RuntimeError as e:
            recv_error.append(str(e))

    rec_thread = threading.Thread(target=_recv, daemon=True)
    rec_thread.start()
    time.sleep(0.05)

    send_ok = False
    try:
        RDTSenderAdapter().send(
            read_file_chunks(src_path),
            send_sock,
            endpoint,
            ctx_send,
        )
        send_ok = True
    except RuntimeError as e:
        pass

    rec_thread.join(timeout=timeout)

    if proxy:
        proxy.stop()

    try:
        send_sock.close()
    except OSError:
        pass
    try:
        rec_sock.close()
    except OSError:
        pass

    recv_ok = bool(recv_ok_flag) and os.path.exists(dst_path)
    return send_ok, recv_ok

class TestRDTFaultInjection(unittest.TestCase):

    TEST_DIR = os.path.dirname(__file__)

    def _path(self, name: str) -> str:
        return os.path.join(self.TEST_DIR, name)

    def setUp(self):
        self.test_src = self._path("_rdt_src.dat")
        self.test_dst = self._path("_rdt_dst.dat")
        write_file(self.test_src, os.urandom(50 * 1024))
        self.src_hash = compute_hash(self.test_src)

    def tearDown(self):
        for f in [self.test_src, self.test_dst]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass

    def test_clean_transfer_sha256(self):
        send_ok, recv_ok = _run_transfer(self.test_src, self.test_dst)
        self.assertTrue(send_ok, "Sender báo fail")
        self.assertTrue(recv_ok, "Receiver báo fail")
        self.assertTrue(os.path.exists(self.test_dst))
        self.assertEqual(self.src_hash, compute_hash(self.test_dst),
                         "SHA-256 không khớp sau transfer sạch")

    def test_packet_loss_recovery(self):
        send_ok, recv_ok = _run_transfer(self.test_src, self.test_dst, drop_rate=0.15)
        self.assertTrue(send_ok, "Sender fail khi có drop 15%")
        self.assertTrue(recv_ok, "Receiver fail khi có drop 15%")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_corruption_recovery(self):
        send_ok, recv_ok = _run_transfer(self.test_src, self.test_dst, corrupt_rate=0.10)
        self.assertTrue(send_ok, "Sender fail khi có corrupt 10%")
        self.assertTrue(recv_ok, "Receiver fail khi có corrupt 10%")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_loss_and_corruption_recovery(self):
        send_ok, recv_ok = _run_transfer(
            self.test_src, self.test_dst,
            drop_rate=0.15, corrupt_rate=0.10,
            retry_limit=20,
        )
        self.assertTrue(send_ok, "Sender fail (drop+corrupt)")
        self.assertTrue(recv_ok, "Receiver fail (drop+corrupt)")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_empty_file_transfer(self):
        src = self._path("_rdt_empty_src.dat")
        dst = self._path("_rdt_empty_dst.dat")
        write_file(src, b"")
        try:
            send_ok, recv_ok = _run_transfer(src, dst, timeout=5.0)
            self.assertTrue(send_ok)
            self.assertTrue(recv_ok)
            self.assertTrue(os.path.exists(dst))
            self.assertEqual(os.path.getsize(dst), 0)
        finally:
            for f in [src, dst]:
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_chunk_boundary_file(self):
        src = self._path("_rdt_exact_src.dat")
        dst = self._path("_rdt_exact_dst.dat")
        write_file(src, os.urandom(2048))
        src_hash = compute_hash(src)
        try:
            send_ok, recv_ok = _run_transfer(src, dst, timeout=5.0)
            self.assertTrue(send_ok)
            self.assertTrue(recv_ok)
            self.assertEqual(src_hash, compute_hash(dst))
        finally:
            for f in [src, dst]:
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_cancel_stops_transfer(self):
        rec_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rec_sock.bind(("127.0.0.1", 0))
        dest_port = rec_sock.getsockname()[1]
        try:
            start = time.time()
            result = send_file_rdt(
                self.test_src, "127.0.0.1", dest_port,
                is_cancelled=lambda: True,
            )
            elapsed = time.time() - start
            self.assertFalse(result, "Sender phải trả False khi bị cancel")
            self.assertLess(elapsed, 3.0, "Cancel phải dừng nhanh, không timeout hết")
        finally:
            rec_sock.close()

    def test_ack_loss_recovery(self):
        send_ok, recv_ok = _run_transfer(
            self.test_src, self.test_dst,
            drop_ack_rate=0.20,
            retry_limit=20,
        )
        self.assertTrue(send_ok, "Sender fail khi mất ACK 20%")
        self.assertTrue(recv_ok, "Receiver fail khi mất ACK 20%")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_max_retry_exhausted_is_finite(self):
        start = time.time()
        send_ok, recv_ok = _run_transfer(
            self.test_src, self.test_dst,
            drop_rate=1.0,      
            retry_limit=3,       
            timeout=10.0,
        )
        elapsed = time.time() - start
        self.assertFalse(send_ok, "Sender phải fail khi drop 100%")
        self.assertLess(elapsed, 8.0, "Phải kết thúc hữu hạn, không treo")

class TestRDTAdapterFaultInjection(unittest.TestCase):
    TEST_DIR = os.path.dirname(__file__)

    def _path(self, name: str) -> str:
        return os.path.join(self.TEST_DIR, name)

    def setUp(self):
        self.test_src = self._path("_adp_src.dat")
        self.test_dst = self._path("_adp_dst.dat")
        write_file(self.test_src, os.urandom(20 * 1024))
        self.src_hash = compute_hash(self.test_src)

    def tearDown(self):
        for f in [self.test_src, self.test_dst]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass

    def test_adapter_clean_transfer_sha256(self):
        send_ok, recv_ok = _run_transfer_adapter(self.test_src, self.test_dst)
        self.assertTrue(send_ok, "Adapter sender báo fail")
        self.assertTrue(recv_ok, "Adapter receiver báo fail")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_adapter_packet_loss_recovery(self):
        send_ok, recv_ok = _run_transfer_adapter(
            self.test_src, self.test_dst,
            drop_rate=0.15, retry_limit=20,
        )
        self.assertTrue(send_ok)
        self.assertTrue(recv_ok)
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_adapter_ack_loss_recovery(self):
        send_ok, recv_ok = _run_transfer_adapter(
            self.test_src, self.test_dst,
            drop_ack_rate=0.20, retry_limit=20,
        )
        self.assertTrue(send_ok)
        self.assertTrue(recv_ok)
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_adapter_empty_file(self):
        src = self._path("_adp_empty_src.dat")
        dst = self._path("_adp_empty_dst.dat")
        write_file(src, b"")
        try:
            send_ok, recv_ok = _run_transfer_adapter(src, dst, timeout=5.0)
            self.assertTrue(send_ok)
            self.assertTrue(recv_ok)
            self.assertEqual(os.path.getsize(dst), 0)
        finally:
            for f in [src, dst]:
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_adapter_cancel_stops_transfer(self):
        transfer_id = random.randint(1, 0xFFFFFFFF)

        rec_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rec_sock.bind(("127.0.0.1", 0))
        dest_port = rec_sock.getsockname()[1]

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_sock.bind(("127.0.0.1", 0))

        endpoint = _SimpleEndpoint("127.0.0.1", dest_port)
        ctx = _SimpleContext(transfer_id, retry_limit=5)
        ctx.cancel_event.set()  # cancel ngay từ đầu

        try:
            start = time.time()
            with self.assertRaises(RuntimeError):
                RDTSenderAdapter().send(
                    read_file_chunks(self.test_src),
                    send_sock,
                    endpoint,
                    ctx,
                )
            elapsed = time.time() - start
            self.assertLess(elapsed, 3.0, "Cancel phải dừng nhanh")
        finally:
            rec_sock.close()
            send_sock.close()

if __name__ == "__main__":
    unittest.main()