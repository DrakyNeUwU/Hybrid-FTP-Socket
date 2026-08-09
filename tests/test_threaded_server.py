"""
test_threaded_server.py — unit tests for FTPServer multithreading

=== WHAT THIS TEST COVERS ===
  1. The server listens for TCP connections on the selected port.
  2. A client receives banner 220, sends echo, and quits successfully.
  3. Multiple clients connect concurrently and receive correct replies.
  4. The server stops cleanly and disconnects all clients.

=== RUN ===
  py -m pytest tests/test_threaded_server.py -v
"""

import os
import sys
import socket
import time
import threading
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.threaded_server import FTPServer, _redact_command

TEST_HOST = "127.0.0.1"
TEST_PORT = 21210  # Dedicated port to avoid the real server.


@pytest.fixture
def running_server():
    """
    Start FTPServer in a background thread before each test and stop it after.
    """
    server = FTPServer(host=TEST_HOST, port=TEST_PORT)
    
    # Run server.start() in a background thread.
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Allow the server socket to bind and listen.
    time.sleep(0.2)
    
    yield server

    # Sau khi test xong -> Cleanup
    server.stop()
    server_thread.join(timeout=1.0)


class TestThreadedServer:
    """Test cases for the multithreaded server."""

    def test_single_client_connection(self, running_server):
        """Check one client can connect, send a command, and disconnect safely."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TEST_HOST, TEST_PORT))

        # 1. Receive the 220 welcome banner.
        banner = s.recv(1024).decode('utf-8')
        assert "220" in banner

        # 2. Send a valid FTP command.
        s.sendall(b"NOOP\r\n")
        response = s.recv(1024).decode('utf-8')
        assert "200 NOOP OK" in response

        # 3. Send QUIT.
        s.sendall(b"QUIT\r\n")
        quit_resp = s.recv(1024).decode('utf-8')
        assert "221" in quit_resp

        s.close()

    def test_concurrent_clients(self, running_server):
        """
        Check ten concurrent client connections without races or deadlocks.
        """
        client_count = 10
        errors = []
        threads = []

        def worker_client(client_id: int):
            try:
                cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cs.connect((TEST_HOST, TEST_PORT))

                # Receive the banner.
                banner = cs.recv(1024).decode('utf-8')
                if "220" not in banner:
                    errors.append(f"Client {client_id}: Banner error")

                # Send an FTP command that does not change session state.
                cs.sendall(b"NOOP\r\n")

                resp = cs.recv(1024).decode('utf-8')
                if "200 NOOP OK" not in resp:
                    errors.append(f"Client {client_id}: NOOP mismatch -> {resp}")

                # Briefly retain concurrent connections.
                time.sleep(0.1)

                cs.sendall(b"QUIT\r\n")
                cs.close()
            except Exception as e:
                errors.append(f"Client {client_id} exception: {e}")

        # Create and start ten client threads together.
        for i in range(client_count):
            t = threading.Thread(target=worker_client, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all client threads to finish.
        for t in threads:
            t.join(timeout=3.0)

        # Verify that no errors occurred.
        assert len(errors) == 0, f"Concurrent-test errors: {errors}"
        
        # Ensure QUIT returns the active-client count to zero.
        time.sleep(0.1)
        assert running_server.get_active_client_count() == 0

    def test_server_stop_cleanup(self):
        """Check that stopping the server disconnects all active clients."""
        clean_port = TEST_PORT + 25
        server = FTPServer(host=TEST_HOST, port=clean_port)
        t = threading.Thread(target=server.start, daemon=True)
        t.start()
        time.sleep(0.3)

        # Open one client socket.
        cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cs.connect((TEST_HOST, clean_port))
        cs.recv(1024)

        assert server.get_active_client_count() == 1

        # Send QUIT so ClientHandler exits completely.
        cs.sendall(b"QUIT\r\n")
        cs.recv(1024)
        cs.close()
        time.sleep(0.1)

        # Stop server
        server.stop()
        assert server.get_active_client_count() == 0

    def test_stop_with_connected_client_does_not_deadlock(self):
        """stop() must close an open client without deadlocking itself."""
        port = TEST_PORT + 26
        server = FTPServer(host=TEST_HOST, port=port)
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        time.sleep(0.2)

        client = socket.create_connection((TEST_HOST, port), timeout=1)
        client.recv(1024)
        time.sleep(0.05)

        sessions = server.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"].startswith("S")

        stop_thread = threading.Thread(target=server.stop)
        stop_thread.start()
        stop_thread.join(timeout=2)

        assert not stop_thread.is_alive(), "server.stop() deadlocked"
        assert server.get_active_client_count() == 0
        client.close()
        server_thread.join(timeout=1)

    def test_password_is_redacted_from_log(self):
        assert _redact_command("PASS secret-password") == "PASS ********"
        assert _redact_command("pass secret-password") == "pass ********"
        assert _redact_command("USER khanh") == "USER khanh"
