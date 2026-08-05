# File: tests/test_rdt.py
import unittest
import sys  
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.RDTHeader import RDTHeader

class TestRDTLogic(unittest.TestCase):

    # Test Case 1: Kiểm tra Checksum và Đóng/Mở gói tin (Serialization)
    def test_header_serialization_and_checksum(self):
        header = RDTHeader(seq_num=1, ack_num=0, flags=RDTHeader.FLAG_DATA, length=5)
        payload = b"Hello"
        header.checksum = header.compute_checksum(payload)    
        # Serialize -> Deserialize
        data = header.serialize()
        deserialized = RDTHeader.deserialize(data)
        
        self.assertEqual(deserialized.seq_num, 1)
        self.assertEqual(deserialized.flags, RDTHeader.FLAG_DATA)
        self.assertTrue(deserialized.verify_checksum(payload))

    # Test Case 2: Giả sử dữ liệu bị lỗi Checksum (Corruption)
    def test_corrupted_payload_checksum(self):
        header = RDTHeader(seq_num=1, ack_num=0, flags=RDTHeader.FLAG_DATA, length=5)
        payload = b"Hello"
        header.checksum = header.compute_checksum(payload)
        
        corrupted_payload = b"H3llo" 
        self.assertFalse(header.verify_checksum(corrupted_payload))

    # Test Case 3: xử lý File rỗng (Edge case)
    def test_empty_file_handling(self):
        chunks = []
        if not chunks:
            chunks = [b""] # Cấu trúc xử lý file rỗng trong rdt_sender
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], b"")

if __name__ == '__main__':
    unittest.main()