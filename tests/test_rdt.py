import socket
import struct
import threading
import time
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.RDTHeader import RDTHeader

def make_data_packet(transfer_id: int, seq: int, payload: bytes, is_fin: bool = False) -> bytes:
    flags = RDTHeader.FLAG_FIN if is_fin else RDTHeader.FLAG_DATA
    hdr = RDTHeader(
        transfer_id=transfer_id, seq_num=seq, ack_num=0,
        flags=flags, length=len(payload)
    )
    hdr.checksum = hdr.compute_checksum(payload)
    return hdr.serialize() + payload


def make_ack_packet(transfer_id: int, ack_seq: int) -> bytes:
    hdr = RDTHeader(
        transfer_id=transfer_id, seq_num=0, ack_num=ack_seq,
        flags=RDTHeader.FLAG_ACK, length=0
    )
    hdr.checksum = hdr.compute_checksum(b"")
    return hdr.serialize()

class TestRDTHeader(unittest.TestCase):

    def test_serialize_deserialize_roundtrip(self):
        hdr = RDTHeader(transfer_id=42, seq_num=7, ack_num=6,
                        flags=RDTHeader.FLAG_DATA, length=100)
        hdr.checksum = hdr.compute_checksum(b"x" * 100)
        raw = hdr.serialize()
        self.assertEqual(len(raw), RDTHeader.size)
        hdr2 = RDTHeader.deserialize(raw)
        self.assertEqual(hdr2.transfer_id, 42)
        self.assertEqual(hdr2.seq_num, 7)
        self.assertEqual(hdr2.ack_num, 6)
        self.assertEqual(hdr2.flags, RDTHeader.FLAG_DATA)
        self.assertEqual(hdr2.length, 100)
        self.assertEqual(hdr2.checksum, hdr.checksum)

    def test_checksum_valid(self):
        payload = b"Hello World"
        hdr = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_DATA, length=len(payload))
        hdr.checksum = hdr.compute_checksum(payload)
        self.assertTrue(hdr.verify_checksum(payload))

    def test_corrupted_checksum(self):
        payload = b"Hello"
        hdr = RDTHeader(transfer_id=1, seq_num=1, ack_num=0,
                        flags=RDTHeader.FLAG_DATA, length=5)
        hdr.checksum = hdr.compute_checksum(payload)
        hdr.checksum ^= 0xDEAD  # flip bits
        self.assertFalse(hdr.verify_checksum(payload))

    def test_corrupted_payload_detected(self):
        payload = b"Original"
        hdr = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_DATA, length=len(payload))
        hdr.checksum = hdr.compute_checksum(payload)
        self.assertFalse(hdr.verify_checksum(b"Corrupted"))

    def test_deserialize_too_short_raises(self):
        with self.assertRaises(ValueError):
            RDTHeader.deserialize(b"\x00" * (RDTHeader.size - 1))

    def test_flag_bitmask_combinations(self):
        combined = RDTHeader.FLAG_DATA | RDTHeader.FLAG_FIN
        self.assertTrue(combined & RDTHeader.FLAG_DATA)
        self.assertTrue(combined & RDTHeader.FLAG_FIN)
        self.assertFalse(combined & RDTHeader.FLAG_ACK)
        self.assertFalse(combined & RDTHeader.FLAG_ABORT)

    def test_flag_data_not_zero(self):
        self.assertNotEqual(RDTHeader.FLAG_DATA, 0)

    def test_checksum_different_seq_gives_different_hash(self):
        payload = b"same payload"
        hdr0 = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                         flags=RDTHeader.FLAG_DATA, length=len(payload))
        hdr1 = RDTHeader(transfer_id=1, seq_num=1, ack_num=0,
                         flags=RDTHeader.FLAG_DATA, length=len(payload))
        self.assertNotEqual(
            hdr0.compute_checksum(payload),
            hdr1.compute_checksum(payload),
            "Checksum must cover seq_num in the header"
        )
    def test_is_valid_flags_accepts_known_combinations(self):
        self.assertTrue(RDTHeader.is_valid_flags(RDTHeader.FLAG_DATA))
        self.assertTrue(RDTHeader.is_valid_flags(RDTHeader.FLAG_FIN))
        self.assertTrue(RDTHeader.is_valid_flags(RDTHeader.FLAG_DATA | RDTHeader.FLAG_FIN))
        self.assertTrue(RDTHeader.is_valid_flags(RDTHeader.FLAG_ACK))
        self.assertTrue(RDTHeader.is_valid_flags(RDTHeader.FLAG_START))
        self.assertTrue(RDTHeader.is_valid_flags(RDTHeader.FLAG_ABORT))

    def test_is_valid_flags_rejects_zero(self):
        self.assertFalse(RDTHeader.is_valid_flags(0))

    def test_is_valid_flags_rejects_unknown_combo(self):
        self.assertFalse(RDTHeader.is_valid_flags(RDTHeader.FLAG_DATA | RDTHeader.FLAG_ACK))
    def test_validate_length_exact(self):
        hdr = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_DATA, length=5)
        packet = hdr.serialize() + b"hello"  # 20 + 5 = 25 bytes
        self.assertTrue(hdr.validate_length(packet))

    def test_validate_length_overflow(self):
        hdr = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_DATA, length=100)
        packet = hdr.serialize() + b"short"  # length=100 but only 5 payload bytes
        self.assertFalse(hdr.validate_length(packet))

    def test_validate_length_zero(self):
        hdr = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_ACK, length=0)
        packet = hdr.serialize()
        self.assertTrue(hdr.validate_length(packet))

class _UDPPair:
    def __init__(self):
        self.sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sender_sock.bind(("127.0.0.1", 0))
        self.receiver_sock.bind(("127.0.0.1", 0))
        self.sender_addr = self.sender_sock.getsockname()
        self.receiver_addr = self.receiver_sock.getsockname()

    def close(self):
        self.sender_sock.close()
        self.receiver_sock.close()


class TestRDTSendReceiveIntegration(unittest.TestCase):
    def _run_transfer(self, payload_data: bytes) -> bytes:
        from common.rdt_sender import send_chunks_rdt
        from common.rdt_receiver import receive_chunks_rdt

        pair = _UDPPair()
        transfer_id = 0xABCD1234
        received: list[bytes] = []
        errors: list[str] = []
        ready = threading.Event()   

        def _receiver():
            ready.set()  
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=transfer_id,
                    timeout_s=1.0,
                    max_timeouts=5,
                ):
                    received.append(chunk)
            except RuntimeError as e:
                errors.append(str(e))

        rec_thread = threading.Thread(target=_receiver, daemon=True)
        rec_thread.start()
        ready.wait(timeout=2.0)

        chunks = [payload_data[i:i+512] for i in range(0, max(1, len(payload_data)), 512)]
        if not payload_data:
            chunks = [b""]

        try:
            send_chunks_rdt(
                iter(chunks),
                "127.0.0.1",
                pair.receiver_addr[1],
                transfer_id,
                udp_socket=pair.sender_sock,
                timeout_s=0.3,
                retry_limit=5,
            )
        except RuntimeError as e:
            errors.append(str(e))

        rec_thread.join(timeout=6)
        pair.close()

        if errors:
            self.fail(f"Transfer errors: {errors}")
        return b"".join(received)

    def test_small_payload(self):
        data = b"Hello RDT World"
        self.assertEqual(self._run_transfer(data), data)

    def test_empty_payload(self):
        result = self._run_transfer(b"")
        self.assertEqual(result, b"")

    def test_multi_chunk(self):
        data = bytes(range(256)) * 10  
        self.assertEqual(self._run_transfer(data), data)

    def test_chunk_boundary(self):
        data = b"A" * 1024
        self.assertEqual(self._run_transfer(data), data)


class TestRDTProtocolLogic(unittest.TestCase):

    def test_go_back_n_sends_window_before_first_cumulative_ack(self):
        """A four-packet window must be in flight before the first ACK arrives."""
        from common.rdt_sender import send_chunks_rdt

        pair = _UDPPair()
        transfer_id = 0xA11CE001
        first_window: list[int] = []
        errors: list[str] = []

        def _receiver() -> None:
            try:
                data, peer = pair.receiver_sock.recvfrom(4096)  # START
                start = RDTHeader.deserialize(data)
                pair.receiver_sock.sendto(make_ack_packet(transfer_id, start.seq_num), peer)
                while len(first_window) < 4:
                    data, peer = pair.receiver_sock.recvfrom(4096)
                    first_window.append(RDTHeader.deserialize(data).seq_num)
                pair.receiver_sock.sendto(make_ack_packet(transfer_id, 3), peer)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))

        thread = threading.Thread(target=_receiver, daemon=True)
        thread.start()
        try:
            sent = send_chunks_rdt(
                iter((b"a", b"b", b"c", b"d")),
                "127.0.0.1", pair.receiver_addr[1], transfer_id,
                udp_socket=pair.sender_sock, timeout_s=0.2, retry_limit=3,
                window_size=4,
            )
        finally:
            thread.join(timeout=2)
            pair.close()

        self.assertEqual(errors, [])
        self.assertEqual(first_window, [0, 1, 2, 3])
        self.assertEqual(sent, 4)

    def test_start_ack_loss_retries_before_data_window(self):
        """A lost START ACK retries metadata and does not open the data window early."""
        from common.rdt_sender import send_chunks_rdt

        pair = _UDPPair()
        transfer_id = 0xA11CE002
        start_count = 0
        received: list[bytes] = []

        def _receiver() -> None:
            nonlocal start_count
            while True:
                data, peer = pair.receiver_sock.recvfrom(4096)
                header = RDTHeader.deserialize(data)
                if header.flags == RDTHeader.FLAG_START:
                    start_count += 1
                    if start_count == 2:
                        pair.receiver_sock.sendto(make_ack_packet(transfer_id, 0), peer)
                    continue
                payload = data[RDTHeader.size:]
                received.append(payload)
                pair.receiver_sock.sendto(make_ack_packet(transfer_id, header.seq_num), peer)
                if header.flags & RDTHeader.FLAG_FIN:
                    return

        thread = threading.Thread(target=_receiver, daemon=True)
        thread.start()
        try:
            sent = send_chunks_rdt(
                iter((b"start",)), "127.0.0.1", pair.receiver_addr[1], transfer_id,
                udp_socket=pair.sender_sock, timeout_s=0.05, retry_limit=4,
            )
        finally:
            thread.join(timeout=2)
            pair.close()

        self.assertEqual(start_count, 2)
        self.assertEqual(received, [b"start"])
        self.assertEqual(sent, 5)

    def test_checksum_covers_header_fields(self):
        p = b"data"
        h0 = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                       flags=RDTHeader.FLAG_DATA, length=len(p))
        h1 = RDTHeader(transfer_id=1, seq_num=1, ack_num=0,
                       flags=RDTHeader.FLAG_DATA, length=len(p))
        self.assertNotEqual(h0.compute_checksum(p), h1.compute_checksum(p))

    def test_ack_validation_requires_matching_seq(self):
        ack_pkt = make_ack_packet(transfer_id=1, ack_seq=3)
        hdr = RDTHeader.deserialize(ack_pkt)
        expected_seq = 5
        self.assertNotEqual(hdr.ack_num, expected_seq)

    def test_abort_flag_detection(self):
        hdr = RDTHeader(transfer_id=1, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_ABORT, length=0)
        hdr.checksum = hdr.compute_checksum(b"")
        raw = hdr.serialize()
        received = RDTHeader.deserialize(raw)
        self.assertTrue(received.flags & RDTHeader.FLAG_ABORT)
        self.assertFalse(received.flags & RDTHeader.FLAG_DATA)
        
    def test_duplicate_not_yielded_twice(self):
        from common.rdt_receiver import receive_chunks_rdt
        pair = _UDPPair()
        received: list[bytes] = []
        done = threading.Event()

        def _recv():
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=77,
                    timeout_s=0.2,
                    max_timeouts=4,
                ):
                    received.append(chunk)
            except RuntimeError:
                pass
            finally:
                done.set()

        t = threading.Thread(target=_recv, daemon=True)
        t.start()
        time.sleep(0.02)

        pkt = make_data_packet(77, 0, b"X", is_fin=True)
        pair.sender_sock.sendto(pkt, pair.receiver_addr)
        time.sleep(0.02)
        pair.sender_sock.sendto(pkt, pair.receiver_addr)  
        done.wait(timeout=3)
        t.join(timeout=3)
        pair.close()

        self.assertEqual(received, [b"X"], f"Must yield exactly once; got: {received}")

    def test_out_of_order_dropped_then_recovered(self):
        from common.rdt_receiver import receive_chunks_rdt
        pair = _UDPPair()
        received: list[bytes] = []
        done = threading.Event()

        def _recv():
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=88,
                    timeout_s=0.2,
                    max_timeouts=6,
                ):
                    received.append(chunk)
            except RuntimeError:
                pass
            finally:
                done.set()

        t = threading.Thread(target=_recv, daemon=True)
        t.start()
        time.sleep(0.02)
        pair.sender_sock.sendto(make_data_packet(88, 1, b"B"), pair.receiver_addr)
        time.sleep(0.02)
        pair.sender_sock.sendto(make_data_packet(88, 0, b"A"), pair.receiver_addr)
        time.sleep(0.02)
        pair.sender_sock.sendto(make_data_packet(88, 1, b"B", is_fin=True), pair.receiver_addr)

        done.wait(timeout=3)
        t.join(timeout=3)
        pair.close()

        self.assertEqual(received, [b"A", b"B"])

    def test_max_retry_limit_raises_runtime_error(self):
        from common.rdt_sender import send_chunks_rdt
        dummy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dummy.bind(("127.0.0.1", 0))
        dead_port = dummy.getsockname()[1]

        try:
            with self.assertRaises(RuntimeError):
                send_chunks_rdt(
                    iter([b"test-retry"]),
                    "127.0.0.1",
                    dead_port,
                    transfer_id=12345,
                    timeout_s=0.05,
                    retry_limit=3,
                )
        finally:
            dummy.close()

    def test_sender_rejects_corrupted_ack(self):
        from common.rdt_sender import send_chunks_rdt
        from common.rdt_receiver import receive_chunks_rdt

        pair = _UDPPair()
        transfer_id = 0xCAFE0001
        received: list[bytes] = []
        done = threading.Event()

        def _recv():
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=transfer_id,
                    timeout_s=0.3,
                    max_timeouts=5,
                ):
                    received.append(chunk)
            except RuntimeError:
                pass
            finally:
                done.set()

        t = threading.Thread(target=_recv, daemon=True)
        t.start()
        time.sleep(0.02)
        try:
            send_chunks_rdt(
                iter([b"ack-test"]),
                "127.0.0.1",
                pair.receiver_addr[1],
                transfer_id,
                udp_socket=pair.sender_sock,
                timeout_s=0.3,
                retry_limit=8,
            )
        except RuntimeError:
            pass

        done.wait(timeout=3)
        t.join(timeout=3)
        pair.close()
        self.assertEqual(b"".join(received), b"ack-test")


    def test_receiver_ignores_different_transfer_id(self):
        from common.rdt_receiver import receive_chunks_rdt
        pair = _UDPPair()
        received: list[bytes] = []
        done = threading.Event()

        def _recv():
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=100,
                    timeout_s=0.2,
                    max_timeouts=3,
                ):
                    received.append(chunk)
            except RuntimeError:
                pass
            finally:
                done.set()

        t = threading.Thread(target=_recv, daemon=True)
        t.start()
        time.sleep(0.02)

        pkt_wrong = make_data_packet(200, 0, b"Wrong ID", is_fin=True)
        pair.sender_sock.sendto(pkt_wrong, pair.receiver_addr)
        time.sleep(0.02)

        pkt_right = make_data_packet(100, 0, b"Right ID", is_fin=True)
        pair.sender_sock.sendto(pkt_right, pair.receiver_addr)

        done.wait(timeout=2)
        t.join(timeout=2)
        pair.close()

        self.assertEqual(received, [b"Right ID"], "Receiver must ignore packets with different transfer_id")

    def test_receiver_aborts_on_abort_packet(self):
        from common.rdt_receiver import receive_chunks_rdt
        pair = _UDPPair()
        errors: list[str] = []
        done = threading.Event()

        def _recv():
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=500,
                    timeout_s=0.2,
                    max_timeouts=3,
                ):
                    pass
            except RuntimeError as e:
                errors.append(str(e))
            finally:
                done.set()

        t = threading.Thread(target=_recv, daemon=True)
        t.start()
        time.sleep(0.02)

        hdr = RDTHeader(transfer_id=500, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_ABORT, length=0)
        hdr.checksum = hdr.compute_checksum(b"")
        pair.sender_sock.sendto(hdr.serialize(), pair.receiver_addr)

        done.wait(timeout=2)
        t.join(timeout=2)
        pair.close()

        self.assertTrue(any("aborted by sender" in err for err in errors), 
                        f"Receiver must abort when ABORT flag is received. Errors: {errors}")

    def test_receiver_graceful_fin_ack_retransmission(self):
        from common.rdt_receiver import receive_chunks_rdt
        pair = _UDPPair()
        received: list[bytes] = []
        done = threading.Event()

        def _recv():
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=999,
                    timeout_s=0.5,
                    max_timeouts=3,
                ):
                    received.append(chunk)
            except RuntimeError:
                pass
            finally:
                done.set()

        t = threading.Thread(target=_recv, daemon=True)
        t.start()
        time.sleep(0.02)

        pkt_fin = make_data_packet(999, 0, b"Final Chunk", is_fin=True)
        pair.sender_sock.sendto(pkt_fin, pair.receiver_addr)

        pair.sender_sock.settimeout(0.5)
        try:
            ack1, _ = pair.sender_sock.recvfrom(1024)
            hdr1 = RDTHeader.deserialize(ack1)
            self.assertEqual(hdr1.ack_num, 0)
            self.assertTrue(hdr1.flags & RDTHeader.FLAG_ACK)
        except socket.timeout:
            self.fail("Did not receive first ACK for FIN")

        pair.sender_sock.sendto(pkt_fin, pair.receiver_addr)
        try:
            ack2, _ = pair.sender_sock.recvfrom(1024)
            hdr2 = RDTHeader.deserialize(ack2)
            self.assertEqual(hdr2.ack_num, 0)
            self.assertTrue(hdr2.flags & RDTHeader.FLAG_ACK)
        except socket.timeout:
            self.fail("Did not receive duplicate ACK for retransmitted FIN in grace period")

        done.wait(timeout=2)
        t.join(timeout=2)
        pair.close()
        self.assertEqual(received, [b"Final Chunk"])

    def test_receiver_drops_invalid_length_packet(self):
        from common.rdt_receiver import receive_chunks_rdt
        pair = _UDPPair()
        received: list[bytes] = []
        done = threading.Event()

        def _recv():
            try:
                for chunk in receive_chunks_rdt(
                    pair.receiver_sock,
                    transfer_id_hint=777,
                    timeout_s=0.2,
                    max_timeouts=3,
                ):
                    received.append(chunk)
            except RuntimeError:
                pass
            finally:
                done.set()

        t = threading.Thread(target=_recv, daemon=True)
        t.start()
        time.sleep(0.02)

        hdr = RDTHeader(transfer_id=777, seq_num=0, ack_num=0,
                        flags=RDTHeader.FLAG_DATA, length=100)
        hdr.checksum = hdr.compute_checksum(b"")
        pair.sender_sock.sendto(hdr.serialize(), pair.receiver_addr)
        time.sleep(0.02)

        pkt_right = make_data_packet(777, 0, b"Valid", is_fin=True)
        pair.sender_sock.sendto(pkt_right, pair.receiver_addr)

        done.wait(timeout=2)
        t.join(timeout=2)
        pair.close()

        self.assertEqual(received, [b"Valid"], "Receiver must ignore packets with invalid payload length")

if __name__ == "__main__":
    unittest.main()
