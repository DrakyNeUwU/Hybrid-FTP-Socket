import unittest
import socket
import threading
import time
import os
import random
from common.rdt_sender import send_file_rdt
from common.rdt_receiver import receive_file_rdt
from common.file_handler import compute_hash, write_file

class NetworkProxy(threading.Thread):
    def __init__(self, listen_port, target_port, drop_rate=0.0, corrupt_rate=0.0):
        super().__init__()
        self.listen_port = listen_port
        self.target_port = target_port
        self.drop_rate = drop_rate
        self.corrupt_rate = corrupt_rate
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', self.listen_port))
        self.sock.settimeout(0.5)

    def run(self):
        last_client_addr = None
        while self.running:
            try:
                data, addr = self.sock.recvfrom(2048)
                if addr[1] != self.target_port:
                    last_client_addr = addr
                    dest = ('127.0.0.1', self.target_port)
                else:
                    dest = last_client_addr

                if random.random() < self.drop_rate:
                    continue

                if random.random() < self.corrupt_rate and len(data) > 10:
                    data_list = bytearray(data)
                    data_list[-1] ^= 0xFF
                    data = bytes(data_list)

                if dest:
                    self.sock.sendto(data, dest)
            except socket.timeout:
                continue
            except (OSError, socket.error):
                break

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


class TestRDTFaultInjection(unittest.TestCase):
    def setUp(self):
        self.test_src = "test_src.dat"
        self.test_dst = "test_dst.dat"
        write_file(self.test_src, os.urandom(50 * 1024))
        self.src_hash = compute_hash(self.test_src)

    def tearDown(self):
        for f in [self.test_src, self.test_dst]:
            if os.path.exists(f):
                os.remove(f)

    def test_loss_and_corruption_recovery(self):
        """Test truyền file qua môi trường rớt gói 15% và corrupt 10%"""
        receiver_port = 9999
        proxy_port = 8888

        rec_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rec_sock.bind(('127.0.0.1', receiver_port))

        proxy = NetworkProxy(listen_port=proxy_port, target_port=receiver_port, drop_rate=0.15, corrupt_rate=0.10)
        proxy.start()

        rec_thread = threading.Thread(target=receive_file_rdt, args=(rec_sock, self.test_dst))
        rec_thread.start()

        time.sleep(0.1)
        send_success = send_file_rdt(self.test_src, '127.0.0.1', proxy_port)

        rec_thread.join(timeout=10)
        proxy.stop()
        rec_sock.close()

        self.assertTrue(send_success)
        self.assertTrue(os.path.exists(self.test_dst))
        
        dst_hash = compute_hash(self.test_dst)
        self.assertEqual(self.src_hash, dst_hash)

    def test_empty_file_transfer(self):
        """Test truyền file rỗng (0-byte) qua RDT"""
        empty_src = "test_empty_src.dat"
        empty_dst = "test_empty_dst.dat"
        write_file(empty_src, b"")

        receiver_port = 9997
        rec_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rec_sock.bind(('127.0.0.1', receiver_port))

        rec_thread = threading.Thread(target=receive_file_rdt, args=(rec_sock, empty_dst))
        rec_thread.start()

        time.sleep(0.1)
        send_success = send_file_rdt(empty_src, '127.0.0.1', receiver_port)

        rec_thread.join(timeout=5)
        rec_sock.close()

        self.assertTrue(send_success)
        self.assertTrue(os.path.exists(empty_dst))
        self.assertEqual(os.path.getsize(empty_dst), 0)

        for f in [empty_src, empty_dst]:
            if os.path.exists(f):
                os.remove(f)

    def test_chunk_aligned_file_transfer(self):
        """Test truyền file có dung lượng bằng đúng bội số của Chunk (VD: 2048 bytes)"""
        exact_src = "test_exact_src.dat"
        exact_dst = "test_exact_dst.dat"
        write_file(exact_src, os.urandom(2048))
        src_hash = compute_hash(exact_src)

        receiver_port = 9996
        rec_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rec_sock.bind(('127.0.0.1', receiver_port))

        rec_thread = threading.Thread(target=receive_file_rdt, args=(rec_sock, exact_dst))
        rec_thread.start()

        time.sleep(0.1)
        send_success = send_file_rdt(exact_src, '127.0.0.1', receiver_port)

        rec_thread.join(timeout=5)
        rec_sock.close()

        self.assertTrue(send_success)
        self.assertTrue(os.path.exists(exact_dst))
        self.assertEqual(src_hash, compute_hash(exact_dst))

        for f in [exact_src, exact_dst]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()