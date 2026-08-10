"""
test_session.py — Unit test cho Session (Role A)
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.session import Session


class TestSession(unittest.TestCase):
    def test_session_initialization(self):
        session = Session(ftp_root="./ftp_root")
        self.assertFalse(session.is_logged_in)
        self.assertIsNone(session.username)
        self.assertEqual(session.transfer_type, "I")
        self.assertEqual(session.transfer_mode, "S")
        self.assertFalse(session.transfer_cancelled)
        self.assertIsNone(session.rename_from)

    def test_session_isolation(self):
        s1 = Session()
        s2 = Session()

        s1.username = "user1"
        s1.is_logged_in = True
        s1.data_mode = "PASV"

        self.assertEqual(s1.username, "user1")
        self.assertTrue(s1.is_logged_in)
        self.assertEqual(s1.data_mode, "PASV")

        self.assertIsNone(s2.username)
        self.assertFalse(s2.is_logged_in)
        self.assertIsNone(s2.data_mode)


if __name__ == "__main__":
    unittest.main()
