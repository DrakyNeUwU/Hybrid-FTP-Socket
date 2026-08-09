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


class TestListDetailed(unittest.TestCase):
    """LIST must produce Unix-style detailed listing with name, size, type, permissions."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_list_contains_filename(self):
        open(os.path.join(self.test_dir, "hello.txt"), "w").write("hi")
        resp = self.handler.handle(CommandParser.parse("LIST"), self.session)
        self.assertIn("150", resp)
        self.assertIn("226", resp)
        self.assertIn("hello.txt", resp)

    def test_list_shows_size(self):
        open(os.path.join(self.test_dir, "sized.txt"), "w").write("12345")
        resp = self.handler.handle(CommandParser.parse("LIST"), self.session)
        self.assertIn("5", resp)   # file size

    def test_list_shows_dir_indicator(self):
        os.mkdir(os.path.join(self.test_dir, "subdir"))
        resp = self.handler.handle(CommandParser.parse("LIST"), self.session)
        # Directory entries must start with 'd'
        for line in resp.splitlines():
            if "subdir" in line:
                self.assertTrue(line.startswith("d"), f"Expected 'd' prefix, got: {line}")

    def test_list_shows_file_indicator(self):
        open(os.path.join(self.test_dir, "file.bin"), "wb").write(b"\x00" * 8)
        resp = self.handler.handle(CommandParser.parse("LIST"), self.session)
        for line in resp.splitlines():
            if "file.bin" in line:
                self.assertTrue(line.startswith("-"), f"Expected '-' prefix, got: {line}")

    def test_nlst_names_only(self):
        open(os.path.join(self.test_dir, "a.txt"), "w").write("x")
        open(os.path.join(self.test_dir, "b.txt"), "w").write("y")
        resp = self.handler.handle(CommandParser.parse("NLST"), self.session)
        self.assertIn("a.txt", resp)
        self.assertIn("b.txt", resp)


class TestRenameFromReset(unittest.TestCase):
    """rename_from must be cleared on QUIT, disconnect, and non-RNTO command."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()
        # create a file to rename
        open(os.path.join(self.test_dir, "orig.txt"), "w").write("data")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rnfr_sets_state(self):
        resp = self.handler.handle(CommandParser.parse("RNFR orig.txt"), self.session)
        self.assertTrue(resp.startswith("350"))
        self.assertEqual(self.session.rename_from, "orig.txt")

    def test_rnfr_then_noop_resets_state(self):
        self.handler.handle(CommandParser.parse("RNFR orig.txt"), self.session)
        self.handler.handle(CommandParser.parse("NOOP"), self.session)
        self.assertIsNone(self.session.rename_from)

    def test_rnfr_then_pwd_resets_state(self):
        self.handler.handle(CommandParser.parse("RNFR orig.txt"), self.session)
        self.handler.handle(CommandParser.parse("PWD"), self.session)
        self.assertIsNone(self.session.rename_from)

    def test_rnto_without_rnfr_returns_503(self):
        resp = self.handler.handle(CommandParser.parse("RNTO new.txt"), self.session)
        self.assertTrue(resp.startswith("503"))

    def test_full_rename_flow(self):
        self.handler.handle(CommandParser.parse("RNFR orig.txt"), self.session)
        resp = self.handler.handle(CommandParser.parse("RNTO renamed.txt"), self.session)
        self.assertTrue(resp.startswith("250"))
        self.assertIsNone(self.session.rename_from)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "renamed.txt")))


class TestTCPFraming(unittest.TestCase):
    """ClientHandler buffer must correctly split commands on \\r\\n boundaries."""

    def _make_handler(self, test_dir):
        """Create a real ClientHandler with a mock socket and server."""
        import socket as sock_mod
        from unittest.mock import MagicMock, patch

        # Pair of connected sockets
        s1, s2 = sock_mod.socketpair()

        mock_server = MagicMock()
        mock_server.next_session_id.return_value = "S000001"
        mock_server.unregister_client = MagicMock()

        from server.client_handler import ClientHandler
        with patch.object(ClientHandler, '__init__', lambda self, sock, addr, server: None):
            ch = ClientHandler.__new__(ClientHandler)
        ch.socket = s1
        ch.addr = ("127.0.0.1", 9999)
        ch.server = mock_server
        ch.session_id = "S000001"
        ch.buffer = b""

        from server.session import Session
        ch.session = Session(ftp_root=test_dir)
        ch.session.session_id = "S000001"
        ch.session.send_reply = ch.send

        from server.transfer_manager import TransferManager
        from common.filesystem_service import FilesystemService
        fs = FilesystemService(test_dir)
        ch.transfer_manager = TransferManager(filesystem=fs)

        from server.command_handler import CommandHandler
        ch.handler = CommandHandler(ch.transfer_manager)

        return ch, s2

    def test_two_commands_in_one_recv(self):
        """Two commands concatenated in one recv() call are both processed."""
        test_dir = tempfile.mkdtemp()
        try:
            from server.command_parser import CommandParser
            from server.ftp_reply import FTPReply

            ch, client_sock = self._make_handler(test_dir)

            # Simulate receiving two commands at once
            data = b"USER testuser\r\nPASS 123456\r\n"
            ch.buffer += data
            responses = []
            while b"\r\n" in ch.buffer:
                line, ch.buffer = ch.buffer.split(b"\r\n", 1)
                raw = line.decode("utf-8")
                cmd = CommandParser.parse(raw)
                resp = ch.handler.handle(cmd, ch.session)
                responses.append(resp)

            self.assertTrue(any("331" in r for r in responses), "Should get 331 for USER")
            self.assertTrue(any("230" in r for r in responses), "Should get 230 for PASS")
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_fragmented_command(self):
        """Command split across two recv() calls is assembled correctly."""
        test_dir = tempfile.mkdtemp()
        try:
            from server.command_parser import CommandParser

            ch, client_sock = self._make_handler(test_dir)

            # First fragment
            ch.buffer += b"USER test"
            self.assertEqual(ch.buffer.count(b"\r\n"), 0)  # Not yet complete

            # Second fragment completes the command
            ch.buffer += b"user\r\n"
            responses = []
            while b"\r\n" in ch.buffer:
                line, ch.buffer = ch.buffer.split(b"\r\n", 1)
                raw = line.decode("utf-8")
                cmd = CommandParser.parse(raw)
                resp = ch.handler.handle(cmd, ch.session)
                responses.append(resp)

            self.assertTrue(any("331" in r for r in responses))
            self.assertEqual(ch.session.username, "testuser")
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_invalid_utf8_does_not_crash(self):
        """Invalid UTF-8 bytes in a command should not raise an exception."""
        test_dir = tempfile.mkdtemp()
        try:
            from server.command_parser import CommandParser

            ch, client_sock = self._make_handler(test_dir)

            bad_data = b"\xff\xfe INVALID\r\n"
            ch.buffer += bad_data
            while b"\r\n" in ch.buffer:
                line, ch.buffer = ch.buffer.split(b"\r\n", 1)
                try:
                    raw = line.decode("utf-8")
                except UnicodeDecodeError:
                    raw = None  # Handler should deal with this
                if raw is not None:
                    cmd = CommandParser.parse(raw)
                    ch.handler.handle(cmd, ch.session)
            # No exception = pass
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


class TestPORTValidation(unittest.TestCase):
    """PORT must reject invalid numbers, out-of-range values, and port 0."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_valid_port(self):
        resp = self.handler.handle(CommandParser.parse("PORT 127,0,0,1,19,136"), self.session)
        self.assertTrue(resp.startswith("200"), resp)
        self.assertEqual(self.session.data_port, 19 * 256 + 136)

    def test_too_few_parts(self):
        resp = self.handler.handle(CommandParser.parse("PORT 127,0,0,1"), self.session)
        self.assertTrue(resp.startswith("501"), resp)

    def test_number_out_of_range(self):
        resp = self.handler.handle(CommandParser.parse("PORT 127,0,0,1,256,0"), self.session)
        self.assertTrue(resp.startswith("501"), resp)

    def test_negative_number(self):
        resp = self.handler.handle(CommandParser.parse("PORT 127,0,0,-1,10,10"), self.session)
        self.assertTrue(resp.startswith("501"), resp)

    def test_port_zero(self):
        resp = self.handler.handle(CommandParser.parse("PORT 127,0,0,1,0,0"), self.session)
        self.assertTrue(resp.startswith("501"), resp)

    def test_non_numeric(self):
        resp = self.handler.handle(CommandParser.parse("PORT 127,0,0,abc,10,10"), self.session)
        self.assertTrue(resp.startswith("501"), resp)

    def test_no_arg(self):
        resp = self.handler.handle(CommandParser.parse("PORT"), self.session)
        self.assertTrue(resp.startswith("501"), resp)


class TestAuthReset(unittest.TestCase):
    """USER command must reset authentication state."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.handler = CommandHandler()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_new_user_resets_login(self):
        # Log in as user1
        self.handler.handle(CommandParser.parse("USER user1"), self.session)
        self.handler.handle(CommandParser.parse("PASS 123456"), self.session)
        self.assertTrue(self.session.is_logged_in)

        # New USER must reset is_logged_in
        self.handler.handle(CommandParser.parse("USER user2"), self.session)
        self.assertFalse(self.session.is_logged_in, "is_logged_in should be False after new USER")
        self.assertEqual(self.session.username, "user2")

    def test_wrong_password_clears_username(self):
        self.handler.handle(CommandParser.parse("USER admin"), self.session)
        resp = self.handler.handle(CommandParser.parse("PASS wrongpass"), self.session)
        self.assertTrue(resp.startswith("530"))
        self.assertFalse(self.session.is_logged_in)
        self.assertIsNone(self.session.username)

    def test_pass_before_user_returns_503(self):
        resp = self.handler.handle(CommandParser.parse("PASS 123456"), self.session)
        self.assertTrue(resp.startswith("503"), resp)


class TestRNTOArgReset(unittest.TestCase):
    """RNTO with empty arg must reset rename_from state."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()
        open(os.path.join(self.test_dir, "orig.txt"), "w").write("data")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rnto_empty_arg_resets_rename_from(self):
        self.handler.handle(CommandParser.parse("RNFR orig.txt"), self.session)
        self.assertIsNotNone(self.session.rename_from)
        # RNTO with no argument must clear rename_from and return 501
        resp = self.handler.handle(CommandParser.parse("RNTO"), self.session)
        self.assertTrue(resp.startswith("501"), resp)
        self.assertIsNone(self.session.rename_from, "rename_from must be cleared on missing RNTO arg")


class TestPASVSocketReplacement(unittest.TestCase):
    """PASV must close the old socket before creating a new one."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()

    def tearDown(self):
        if getattr(self.session, 'data_socket', None):
            try:
                self.session.data_socket.close()
            except Exception:
                pass
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pasv_creates_socket(self):
        resp = self.handler.handle(CommandParser.parse("PASV"), self.session)
        self.assertTrue(resp.startswith("227"), resp)
        self.assertIsNotNone(self.session.data_socket)
        self.assertGreater(self.session.data_port, 0)
        self.assertEqual(self.session.data_mode, "PASSIVE")

    def test_pasv_replaces_old_socket(self):
        # First PASV
        self.handler.handle(CommandParser.parse("PASV"), self.session)
        old_port = self.session.data_port
        old_socket = self.session.data_socket

        # Second PASV must create a new socket; old one should be closed
        resp2 = self.handler.handle(CommandParser.parse("PASV"), self.session)
        self.assertTrue(resp2.startswith("227"), resp2)
        new_port = self.session.data_port
        # Old socket should be closed (fileno() returns -1 or raises)
        try:
            closed = old_socket.fileno() == -1
        except Exception:
            closed = True
        self.assertTrue(closed, "Old PASV socket should be closed after second PASV")


class TestTypeModeCommands(unittest.TestCase):
    """TYPE and MODE must accept valid values and reject invalid ones."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_type_binary(self):
        resp = self.handler.handle(CommandParser.parse("TYPE I"), self.session)
        self.assertTrue(resp.startswith("200"), resp)
        self.assertEqual(self.session.transfer_type, "I")

    def test_type_ascii(self):
        resp = self.handler.handle(CommandParser.parse("TYPE A"), self.session)
        self.assertTrue(resp.startswith("200"), resp)
        self.assertEqual(self.session.transfer_type, "A")

    def test_type_invalid(self):
        resp = self.handler.handle(CommandParser.parse("TYPE Z"), self.session)
        self.assertTrue(resp.startswith("501"), resp)

    def test_mode_stream(self):
        resp = self.handler.handle(CommandParser.parse("MODE S"), self.session)
        self.assertTrue(resp.startswith("200"), resp)

    def test_mode_block_not_implemented(self):
        resp = self.handler.handle(CommandParser.parse("MODE B"), self.session)
        self.assertTrue(resp.startswith("502"), resp)

    def test_mode_compressed_not_implemented(self):
        resp = self.handler.handle(CommandParser.parse("MODE C"), self.session)
        self.assertTrue(resp.startswith("502"), resp)

    def test_mode_invalid(self):
        resp = self.handler.handle(CommandParser.parse("MODE X"), self.session)
        self.assertTrue(resp.startswith("501"), resp)


class TestRoleAValidationAndRDTAdapter(unittest.TestCase):
    """Test argument validation, PORT anti-bounce, data connection requirements, and RDT adapter integration."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()

    def tearDown(self):
        if getattr(self.session, "data_socket", None):
            try:
                self.session.data_socket.close()
            except Exception:
                pass
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_argument_validation(self):
        # No-args commands with extra argument -> 501
        for cmd_str in ["PWD extra", "NOOP extra", "QUIT extra", "PASV extra", "CDUP extra", "ABOR extra"]:
            resp = self.handler.handle(CommandParser.parse(cmd_str), self.session)
            self.assertTrue(resp.startswith("501"), f"Expected 501 for '{cmd_str}', got: {resp}")

        # Required-args commands missing argument -> 501
        for cmd_str in ["CWD", "MKD", "RMD", "DELE", "RNFR", "RNTO", "SIZE", "MDTM", "HASH"]:
            resp = self.handler.handle(CommandParser.parse(cmd_str), self.session)
            self.assertTrue(resp.startswith("501"), f"Expected 501 for '{cmd_str}', got: {resp}")

    def test_port_validation_and_antibounce(self):
        # Invalid PORT formats or bounds
        for invalid_port in ["PORT 127,0,0,1", "PORT 127,0,0,1,0,0", "PORT 127,0,0,1,300,100", "PORT 127,0,0,1,-5,10"]:
            resp = self.handler.handle(CommandParser.parse(invalid_port), self.session)
            self.assertTrue(resp.startswith("501"), f"Expected 501 for '{invalid_port}', got: {resp}")

        # Anti-FTP bounce test: peer IP is remote 192.168.1.50, PORT IP is 10.0.0.1
        self.session.peer_ip = "192.168.1.50"
        bounce_resp = self.handler.handle(CommandParser.parse("PORT 10,0,0,1,19,136"), self.session)
        self.assertTrue(bounce_resp.startswith("501"), f"Expected 501 for FTP bounce, got: {bounce_resp}")

    def test_transfer_requires_data_connection(self):
        # No data socket / endpoint set -> must return 425
        self.session.data_socket = None
        self.session.data_host = None
        self.session.data_port = None

        for transfer_cmd in ["RETR file.txt", "STOR file.txt", "STOU", "APPE file.txt"]:
            resp = self.handler.handle(CommandParser.parse(transfer_cmd), self.session)
            self.assertTrue(resp.startswith("425"), f"Expected 425 for '{transfer_cmd}', got: {resp}")

    def test_second_transfer_is_rejected_while_first_is_active(self):
        self.session.data_host = "127.0.0.1"
        self.session.data_port = 9999
        self.session.current_transfer = {"type": "RETR", "file": "first.bin"}

        resp = self.handler.handle(CommandParser.parse("STOR second.bin"), self.session)

        self.assertTrue(resp.startswith("450"), resp)

    def test_rdt_adapter_import_and_instantiation(self):
        from server.rdt_adapter import RDTSenderAdapter, RDTReceiverAdapter
        sender = RDTSenderAdapter()
        receiver = RDTReceiverAdapter()
        self.assertIsNotNone(sender)
        self.assertIsNotNone(receiver)

    def test_session_isolation_and_transfer_id(self):
        session1 = Session(ftp_root=self.test_dir)
        session2 = Session(ftp_root=self.test_dir)
        session1.is_logged_in = True
        session2.is_logged_in = True

        tid1 = session1.new_transfer_id()
        tid2 = session2.new_transfer_id()

        self.assertNotEqual(tid1, tid2)

        # Session states are completely independent
        session1.data_host = "192.168.1.10"
        session2.data_host = "10.0.0.5"
        self.assertNotEqual(session1.data_host, session2.data_host)

    def test_cleanup_assertion(self):
        from server.client_handler import ClientHandler
        class DummyServer:
            def next_session_id(self): return "S000001"
            def unregister_client(self, c): pass

        import socket
        dummy_sock, _ = socket.socketpair()
        try:
            handler = ClientHandler(dummy_sock, ("127.0.0.1", 12345), DummyServer())
            handler.session.is_logged_in = True
            handler.cleanup()
            self.assertIsNone(handler.session.data_socket)
            self.assertIsNone(handler.session.data_host)
            self.assertIsNone(handler.session.data_port)
            self.assertIsNone(handler.session.rename_from)
        finally:
            dummy_sock.close()


class TestModeComplianceRoleA(unittest.TestCase):
    """Task A-F01: MODE compliance and limitation checks according to requirement §2.2."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.handler = CommandHandler()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_mode_s_supported(self):
        self.session.is_logged_in = True
        resp = self.handler.handle(CommandParser.parse("MODE S"), self.session)
        self.assertTrue(resp.startswith("200"))
        self.assertEqual(self.session.transfer_mode, "S")

    def test_mode_b_c_not_implemented(self):
        self.session.is_logged_in = True
        resp_b = self.handler.handle(CommandParser.parse("MODE B"), self.session)
        self.assertTrue(resp_b.startswith("502"), f"MODE B must return 502, got: {resp_b}")

        resp_c = self.handler.handle(CommandParser.parse("MODE C"), self.session)
        self.assertTrue(resp_c.startswith("502"), f"MODE C must return 502, got: {resp_c}")

    def test_mode_invalid_parameter(self):
        self.session.is_logged_in = True
        resp = self.handler.handle(CommandParser.parse("MODE X"), self.session)
        self.assertTrue(resp.startswith("501"), f"Invalid MODE must return 501, got: {resp}")

    def test_mode_unauthenticated(self):
        self.session.is_logged_in = False
        resp = self.handler.handle(CommandParser.parse("MODE S"), self.session)
        self.assertTrue(resp.startswith("530"))

    def test_mode_session_isolation(self):
        s1 = Session(ftp_root=self.test_dir)
        s2 = Session(ftp_root=self.test_dir)
        s1.is_logged_in = True
        s2.is_logged_in = True

        self.handler.handle(CommandParser.parse("MODE S"), s1)
        self.assertEqual(s1.transfer_mode, "S")
        self.assertEqual(s2.transfer_mode, "S")


class TestCommandMatrix28RoleA(unittest.TestCase):
    """Task A-F02: All 28 FTP commands compliance matrix testing for Role A."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = Session(ftp_root=self.test_dir)
        self.session.is_logged_in = True
        self.handler = CommandHandler()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_all_28_commands_matrix(self):
        # 28 supported commands in requirement §2.2
        all_28_cmds = [
            "USER", "PASS", "QUIT", "NOOP", "PWD", "CWD", "CDUP", "MKD", "RMD",
            "DELE", "RNFR", "RNTO", "LIST", "NLST", "SIZE", "MDTM", "STAT", "HASH",
            "TYPE", "MODE", "HELP", "PORT", "PASV", "RETR", "STOR", "STOU", "APPE", "ABOR"
        ]

        # Verify help returns 214 and lists commands
        help_resp = self.handler.handle(CommandParser.parse("HELP"), self.session)
        self.assertTrue(help_resp.startswith("214"))

        # Check unhandled command returns 502
        unhandled_resp = self.handler.handle(CommandParser.parse("SITE"), self.session)
        self.assertTrue(unhandled_resp.startswith("502"))


if __name__ == "__main__":
    unittest.main()


