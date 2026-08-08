"""
test_threaded_server.py — Unit test kiểm tra tính năng đa luồng của FTPServer

=== TEST NÀY KIỂM TRA GÌ? ===
  1. Server lắng nghe kết nối TCP trên port chỉ định.
  2. Một client kết nối, nhận banner 220, gửi echo và QUIT thành công.
  3. Nhiều client (5-10 clients) kết nối ĐỒNG THỜI:
     - Mọi client đều nhận phản hồi đúng (không bị nghẽn/chờ).
     - Số lượng client active được theo dõi chính xác (Thread-safe tracking).
  4. Server tắt (stop) sạch sẽ và ngắt toàn bộ kết nối client.

=== CÁCH CHẠY ===
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
TEST_PORT = 21210  # Dùng port riêng để tránh đụng độ với server thật


@pytest.fixture
def running_server():
    """
    Fixture khởi chạy FTPServer trong 1 thread ngầm trước test
    và tự động tắt server sau khi test kết thúc.
    """
    server = FTPServer(host=TEST_HOST, port=TEST_PORT)
    
    # Chạy server.start() trong background thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Chờ 0.2s để server socket sẵn sàng bind/listen
    time.sleep(0.2)
    
    yield server

    # Sau khi test xong -> Cleanup
    server.stop()
    server_thread.join(timeout=1.0)


class TestThreadedServer:
    """Tập hợp các test case kiểm tra server đa luồng."""

    def test_single_client_connection(self, running_server):
        """Kiểm tra 1 client kết nối, gửi lệnh và ngắt kết nối an toàn."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TEST_HOST, TEST_PORT))

        # 1. Nhận banner chào mừng 220
        banner = s.recv(1024).decode('utf-8')
        assert "220" in banner

        # 2. Gửi FTP command hợp lệ
        s.sendall(b"NOOP\r\n")
        response = s.recv(1024).decode('utf-8')
        assert "200 NOOP OK" in response

        # 3. Gửi QUIT
        s.sendall(b"QUIT\r\n")
        quit_resp = s.recv(1024).decode('utf-8')
        assert "221" in quit_resp

        s.close()

    def test_concurrent_clients(self, running_server):
        """
        Kiểm tra 10 client kết nối ĐỒNG THỜI (Concurrent connections).
        Đảm bảo không race-condition, không deadlock và phản hồi chính xác.
        """
        client_count = 10
        errors = []
        threads = []

        def worker_client(client_id: int):
            try:
                cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cs.connect((TEST_HOST, TEST_PORT))

                # Nhận banner
                banner = cs.recv(1024).decode('utf-8')
                if "220" not in banner:
                    errors.append(f"Client {client_id}: Banner error")

                # Gửi FTP command không thay đổi session state.
                cs.sendall(b"NOOP\r\n")

                resp = cs.recv(1024).decode('utf-8')
                if "200 NOOP OK" not in resp:
                    errors.append(f"Client {client_id}: NOOP mismatch -> {resp}")

                # Chờ nhẹ 0.1s để giữ kết nối đồng thời
                time.sleep(0.1)

                cs.sendall(b"QUIT\r\n")
                cs.close()
            except Exception as e:
                errors.append(f"Client {client_id} exception: {e}")

        # Khởi tạo và chạy 10 client threads cùng lúc
        for i in range(client_count):
            t = threading.Thread(target=worker_client, args=(i,))
            threads.append(t)
            t.start()

        # Đợi tất cả 10 client hoàn thành
        for t in threads:
            t.join(timeout=3.0)

        # Kiểm tra không có lỗi nào phát sinh
        assert len(errors) == 0, f"Các lỗi phát sinh khi test đồng thời: {errors}"
        
        # Đảm bảo sau khi các client QUIT, active client count giảm về 0
        time.sleep(0.1)
        assert running_server.get_active_client_count() == 0

    def test_server_stop_cleanup(self):
        """Kiểm tra việc stop server ngắt toàn bộ kết nối active."""
        clean_port = TEST_PORT + 25
        server = FTPServer(host=TEST_HOST, port=clean_port)
        t = threading.Thread(target=server.start, daemon=True)
        t.start()
        time.sleep(0.3)

        # Mở 1 socket kết nối
        cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cs.connect((TEST_HOST, clean_port))
        cs.recv(1024)

        assert server.get_active_client_count() == 1

        # Gửi QUIT để ClientHandler thoát hẳn
        cs.sendall(b"QUIT\r\n")
        cs.recv(1024)
        cs.close()
        time.sleep(0.1)

        # Stop server
        server.stop()
        assert server.get_active_client_count() == 0

    def test_stop_with_connected_client_does_not_deadlock(self):
        """stop() phải đóng client đang mở mà không tự khóa chính nó."""
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

        assert not stop_thread.is_alive(), "server.stop() bị deadlock"
        assert server.get_active_client_count() == 0
        client.close()
        server_thread.join(timeout=1)

    def test_password_is_redacted_from_log(self):
        assert _redact_command("PASS secret-password") == "PASS ********"
        assert _redact_command("pass secret-password") == "pass ********"
        assert _redact_command("USER khanh") == "USER khanh"
