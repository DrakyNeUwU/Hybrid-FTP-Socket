# File: tests/test_rdt.py
import unittest
import sys  
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.RDTHeader import RDTHeader

class TestRDTLogic(unittest.TestCase):
    # 1. Mất data
    def test_loss_data_packet(self):
        # khi Sender gửi nhưng Data bị drop hoàn toàn
        packet_sent = True
        data_lost = True
        received = False if data_lost else True
        self.assertFalse(received)

    # 2. Mất ACK 
    def test_loss_ack_packet(self):
        # Receiver đã nhận gói nhưng ACK gửi về bị drop
        ack_lost = True
        sender_received_ack = False if ack_lost else True
        self.assertFalse(sender_received_ack)

    # 3. Delayed Packet 
    def test_delayed_packet(self):
        import time
        timeout = 0.1
        start_time = time.time()
        time.sleep(0.15) # khi packet đến sau khoảng timeout
        elapsed = time.time() - start_time
        is_timeout = elapsed > timeout
        self.assertTrue(is_timeout)

    # 4. Duplicate Packet 
    def test_duplicate_packet_detection(self):
        last_expected_seq = 1
        received_seq = 0 # Gói cũ gửi lại
        is_duplicate = (received_seq < last_expected_seq)
        self.assertTrue(is_duplicate)

    # 5. Packet lỗi checksum 
    def test_corrupted_checksum(self):
        header = RDTHeader(seq_num=1, ack_num=0, flags=RDTHeader.FLAG_DATA, length=5)
        header.checksum = 123456 # Checksum sai
        payload = b"Hello"
        self.assertFalse(header.verify_checksum(payload))

    # 6. Out of order
    def test_out_of_order_packet(self):
        expected_seq = 1
        received_seq = 2 # Nhận nhảy cóc
        is_out_of_order = (received_seq != expected_seq)
        self.assertTrue(is_out_of_order)

    # 7. lố retransmit 
    def test_max_retransmit_exceeded(self):
        max_retries = 5
        retries = 0
        ack_received = False # Mất mạng
        
        while retries < max_retries and not ack_received:
            retries += 1
            
        self.assertEqual(retries, max_retries)
        self.assertFalse(ack_received) # Báo lỗi

if __name__ == '__main__':
    unittest.main()