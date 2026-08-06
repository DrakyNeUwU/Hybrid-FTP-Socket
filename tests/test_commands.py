"""
test_commands.py — Unit test cho CommandHandler (Role A)
"""

import unittest
import sys
import os
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.command_handler import CommandHandler
from server.command_parser import CommandParser
from server.session import Session


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.handler = CommandHandler()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_unauthenticated_access(self):
        cmd = CommandParser.parse("PWD")
        resp = self.handler.handle(cmd, self.session)
        self.assertTrue(resp.startswith("530"))

        cmd_cwd = CommandParser.parse("CWD sub")
        resp_cwd = self.handler.handle(cmd_cwd, self.session)
        self.assertTrue(resp_cwd.startswith("530"))

    def test_auth_flow(self):
        # 1. USER
        user_cmd = CommandParser.parse("USER testuser")
        resp = self.handler.handle(user_cmd, self.session)
        self.assertTrue(resp.startswith("331"))
        self.assertEqual(self.session.username, "testuser")

        # 2. PASS
        pass_cmd = CommandParser.parse("PASS 123456")
        resp_pass = self.handler.handle(pass_cmd, self.session)
        self.assertTrue(resp_pass.startswith("230"))
        self.assertTrue(self.session.is_logged_in)

    def test_directory_commands(self):
        # Log in
        self.session.username = "testuser"
        self.session.is_logged_in = True

        # PWD
        resp_pwd = self.handler.handle(CommandParser.parse("PWD"), self.session)
        self.assertTrue(resp_pwd.startswith("257"))

        # MKD
        resp_mkd = self.handler.handle(CommandParser.parse("MKD test_sub"), self.session)
        self.assertTrue(resp_mkd.startswith("257"))

        # CWD
        resp_cwd = self.handler.handle(CommandParser.parse("CWD test_sub"), self.session)
        self.assertTrue(resp_cwd.startswith("250"))

        # CDUP
        resp_cdup = self.handler.handle(CommandParser.parse("CDUP"), self.session)
        self.assertTrue(resp_cdup.startswith("200"))

        # Traversal Prevention
        resp_bad_cwd = self.handler.handle(CommandParser.parse("CWD ../.."), self.session)
        self.assertTrue(resp_bad_cwd.startswith("550"))

        # RMD
        resp_rmd = self.handler.handle(CommandParser.parse("RMD test_sub"), self.session)
        self.assertTrue(resp_rmd.startswith("250"))

    def test_metadata_and_file_ops(self):
        self.session.username = "testuser"
        self.session.is_logged_in = True

        # Create dummy file
        filepath = os.path.join(self.test_dir, "sample.txt")
        with open(filepath, "w") as f:
            f.write("Hello FTP World!")

        # SIZE
        resp_size = self.handler.handle(CommandParser.parse("SIZE sample.txt"), self.session)
        self.assertTrue(resp_size.startswith("213"))
        self.assertIn("16", resp_size)

        # MDTM
        resp_mdtm = self.handler.handle(CommandParser.parse("MDTM sample.txt"), self.session)
        self.assertTrue(resp_mdtm.startswith("213"))

        # HASH
        resp_hash = self.handler.handle(CommandParser.parse("HASH sample.txt"), self.session)
        self.assertTrue(resp_hash.startswith("213 SHA256"))

        # RNFR & RNTO
        resp_rnfr = self.handler.handle(CommandParser.parse("RNFR sample.txt"), self.session)
        self.assertTrue(resp_rnfr.startswith("350"))
        resp_rnto = self.handler.handle(CommandParser.parse("RNTO renamed.txt"), self.session)
        self.assertTrue(resp_rnto.startswith("250"))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "renamed.txt")))

        # DELE
        resp_dele = self.handler.handle(CommandParser.parse("DELE renamed.txt"), self.session)
        self.assertTrue(resp_dele.startswith("250"))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "renamed.txt")))

    def test_pasv_and_port(self):
        self.session.username = "testuser"
        self.session.is_logged_in = True

        # PASV
        resp_pasv = self.handler.handle(CommandParser.parse("PASV"), self.session)
        self.assertTrue(resp_pasv.startswith("227"))
        self.assertEqual(self.session.data_mode, "PASSIVE")

        # Clean passive socket
        if self.session.data_socket:
            self.session.data_socket.close()

        # PORT
        resp_port = self.handler.handle(CommandParser.parse("PORT 127,0,0,1,19,136"), self.session)
        self.assertTrue(resp_port.startswith("200"))
        self.assertEqual(self.session.data_mode, "ACTIVE")
        self.assertEqual(self.session.data_host, "127.0.0.1")
        self.assertEqual(self.session.data_port, 5000)

    def test_noop_help_abor(self):
        self.session.username = "testuser"
        self.session.is_logged_in = True

        resp_noop = self.handler.handle(CommandParser.parse("NOOP"), self.session)
        self.assertTrue(resp_noop.startswith("200"))

        resp_help = self.handler.handle(CommandParser.parse("HELP"), self.session)
        self.assertTrue(resp_help.startswith("214"))

        resp_abor = self.handler.handle(CommandParser.parse("ABOR"), self.session)
        self.assertTrue(resp_abor.startswith("226"))
        self.assertTrue(self.session.transfer_cancelled)


if __name__ == "__main__":
    unittest.main()
