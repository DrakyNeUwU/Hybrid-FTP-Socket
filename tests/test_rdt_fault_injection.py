"""Fault injection tests cho RDT layer — Role B.

Tests này dùng NetworkProxy mô phỏng mất gói (drop) và corrupt để
verify rằng Send/Receive RDT phục hồi đúng và file đến nguyên vẹn.

Fixes:
- B-T1: NetworkProxy dùng dynamic port (bind 0), không cần listen_port cứng.
- B-T2: Thêm _run_transfer_adapter() gọi RDTSenderAdapter/RDTReceiverAdapter.
- B-T3: Thêm test mất ACK, mất ACK FIN, ABORT, hết retry.
- B-T4: test_loss_and_corruption_recovery chạy lại đúng sau khi sửa _fin_grace.
- B-T5 (NetworkProxy): drop_ack_rate để mô phỏng mất ACK riêng biệt.
"""

import os
import random
import socket
import threading
import time
import unittest

from common.rdt_sender import send_file_rdt, RDTSenderAdapter
from common.rdt_receiver import receive_file_rdt, RDTReceiverAdapter
from common.file_handler import compute_hash, write_file, write_file_from_chunks, read_file_chunks


# ---------------------------------------------------------------------------
# NetworkProxy — dynamic port, hỗ trợ drop ACK riêng (B-T1, B-T5)
# ---------------------------------------------------------------------------

class NetworkProxy(threading.Thread):
    """Proxy UDP hai chiều với drop/corrupt có thể cài đặt.

    B-T1 fix: bind đến port 0 (dynamic), trả listen_port qua attribute.
    B-T5: thêm drop_ack_rate để mô phỏng mất ACK từ receiver về sender.
    """

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

        # B-T1: bind dynamic port — không cần chỉ định listen_port từ bên ngoài
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.listen_port = self.sock.getsockname()[1]  # port thực tế được cấp
        self.sock.settimeout(0.3)

        # map port → full addr, tránh None khi ACK đến trước packet
        self._client_map: dict[int, tuple] = {}

    def run(self) -> None:
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            # Phân loại hướng
            from_receiver = addr[1] == self.target_port
            if not from_receiver:
                # Từ sender → ghi nhớ, forward đến target
                self._client_map[addr[1]] = addr
                dest = ("127.0.0.1", self.target_port)
                # Drop DATA packet
                if random.random() < self.drop_rate:
                    continue
            else:
                # ACK từ receiver → forward về sender
                if not self._client_map:
                    continue
                dest = next(iter(self._client_map.values()))
                # B-T5: drop ACK riêng
                if random.random() < self.drop_ack_rate:
                    continue
                # Drop ACK theo drop_rate chung
                if random.random() < self.drop_rate:
                    continue

            # Corrupt (cả hai chiều)
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


# ---------------------------------------------------------------------------
# Simple context/endpoint objects cho production adapter tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_transfer(
    src_path: str,
    dst_path: str,
    drop_rate: float = 0.0,
    corrupt_rate: float = 0.0,
    drop_ack_rate: float = 0.0,
    timeout: float = 20.0,
    retry_limit: int = 15,
) -> tuple[bool, bool]:
    """Chạy send+receive (legacy API) song song qua NetworkProxy.

    B-T1 fix: không dùng port cố định — NetworkProxy bind dynamic.
    """
    # B-T1: receiver socket dynamic
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
        actual_dest_port = proxy.listen_port   # B-T1: port thực từ proxy

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
    """Chạy send+receive qua RDTSenderAdapter / RDTReceiverAdapter (B-T2 fix).

    Đây là production path: không gọi legacy API.
    B-S1 fix: sender dùng external socket được truyền vào.
    """
    transfer_id = random.randint(1, 0xFFFFFFFF)

    # B-T1: tất cả socket dynamic
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
            # production path: generator → write atomically
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
        # B-S1: truyền send_sock — adapter sẽ dùng socket này
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


# ---------------------------------------------------------------------------
# Tests — Legacy API (B-T1 fixed ports → dynamic)
# ---------------------------------------------------------------------------

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
        """Transfer sạch không drop/corrupt — SHA-256 phải khớp."""
        send_ok, recv_ok = _run_transfer(self.test_src, self.test_dst)
        self.assertTrue(send_ok, "Sender báo fail")
        self.assertTrue(recv_ok, "Receiver báo fail")
        self.assertTrue(os.path.exists(self.test_dst))
        self.assertEqual(self.src_hash, compute_hash(self.test_dst),
                         "SHA-256 không khớp sau transfer sạch")

    def test_packet_loss_recovery(self):
        """Drop 15% gói → sender phải retransmit, file vẫn đến nguyên vẹn."""
        send_ok, recv_ok = _run_transfer(self.test_src, self.test_dst, drop_rate=0.15)
        self.assertTrue(send_ok, "Sender fail khi có drop 15%")
        self.assertTrue(recv_ok, "Receiver fail khi có drop 15%")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_corruption_recovery(self):
        """Corrupt 10% gói → checksum bắt lỗi, sender retransmit."""
        send_ok, recv_ok = _run_transfer(self.test_src, self.test_dst, corrupt_rate=0.10)
        self.assertTrue(send_ok, "Sender fail khi có corrupt 10%")
        self.assertTrue(recv_ok, "Receiver fail khi có corrupt 10%")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_loss_and_corruption_recovery(self):
        """Drop 15% + corrupt 10% — SHA-256 phải vẫn khớp (B-T4 fix qua B-R6)."""
        send_ok, recv_ok = _run_transfer(
            self.test_src, self.test_dst,
            drop_rate=0.15, corrupt_rate=0.10,
            retry_limit=20,
        )
        self.assertTrue(send_ok, "Sender fail (drop+corrupt)")
        self.assertTrue(recv_ok, "Receiver fail (drop+corrupt)")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_empty_file_transfer(self):
        """File rỗng (0 byte) phải transfer thành công."""
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
        """File đúng bội số chunk (2048 bytes) — không bỏ sót byte."""
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
        """is_cancelled=True ngay từ đầu → sender phải dừng nhanh."""
        # Cần receiver socket để sender gửi START trước
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

    # B-T3: mất ACK từ receiver → sender retransmit, file vẫn đúng
    def test_ack_loss_recovery(self):
        """Drop 20% ACK từ receiver → sender retransmit, SHA-256 khớp."""
        send_ok, recv_ok = _run_transfer(
            self.test_src, self.test_dst,
            drop_ack_rate=0.20,
            retry_limit=20,
        )
        self.assertTrue(send_ok, "Sender fail khi mất ACK 20%")
        self.assertTrue(recv_ok, "Receiver fail khi mất ACK 20%")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    # B-T3: hết retry → cleanup hữu hạn (không treo vô hạn)
    def test_max_retry_exhausted_is_finite(self):
        """Khi drop 100% → sender hết retry hữu hạn, không treo mãi."""
        start = time.time()
        send_ok, recv_ok = _run_transfer(
            self.test_src, self.test_dst,
            drop_rate=1.0,       # drop tất cả DATA
            retry_limit=3,       # ít retry để test nhanh
            timeout=10.0,
        )
        elapsed = time.time() - start
        # Phải fail (không send được)
        self.assertFalse(send_ok, "Sender phải fail khi drop 100%")
        # Phải kết thúc hữu hạn
        self.assertLess(elapsed, 8.0, "Phải kết thúc hữu hạn, không treo")


# ---------------------------------------------------------------------------
# Tests — Production Adapter (B-T2 fix)
# ---------------------------------------------------------------------------

class TestRDTAdapterFaultInjection(unittest.TestCase):
    """Fault injection tests dùng RDTSenderAdapter/RDTReceiverAdapter production."""

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
        """Production adapter: transfer sạch — SHA-256 phải khớp."""
        send_ok, recv_ok = _run_transfer_adapter(self.test_src, self.test_dst)
        self.assertTrue(send_ok, "Adapter sender báo fail")
        self.assertTrue(recv_ok, "Adapter receiver báo fail")
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_adapter_packet_loss_recovery(self):
        """Production adapter: drop 15% → retransmit, SHA-256 khớp."""
        send_ok, recv_ok = _run_transfer_adapter(
            self.test_src, self.test_dst,
            drop_rate=0.15, retry_limit=20,
        )
        self.assertTrue(send_ok)
        self.assertTrue(recv_ok)
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_adapter_ack_loss_recovery(self):
        """Production adapter: mất 20% ACK → sender retransmit, file đúng."""
        send_ok, recv_ok = _run_transfer_adapter(
            self.test_src, self.test_dst,
            drop_ack_rate=0.20, retry_limit=20,
        )
        self.assertTrue(send_ok)
        self.assertTrue(recv_ok)
        self.assertEqual(self.src_hash, compute_hash(self.test_dst))

    def test_adapter_empty_file(self):
        """Production adapter: file rỗng → transfer thành công."""
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
        """Production adapter: cancel_event được set → sender dừng nhanh."""
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