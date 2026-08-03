"""
threaded_server.py — Khung Server đa luồng cho Hybrid FTP

=== FILE NÀY GIẢI QUYẾT GÌ? ===
Quản lý việc lắng nghe kết nối TCP từ nhiều Client cùng lúc:
  - Khởi tạo Socket Server (bind/listen).
  - Vòng lặp accept kết nối mới.
  - Tạo luồng (Thread) riêng cho mỗi Client kết nối để xử lý độc lập (không block lẫn nhau).
  - Đảm bảo an toàn đa luồng (Thread-safety) khi log hoặc quản lý danh sách client.

=== KẾT NỐI VỚI FILE NÀO? ===
  - common/dir_manager.py & common/file_handler.py (khi xử lý lệnh filesystem)
  - Role A: gọi module parse lệnh và xử lý session TCP
  - Role B: kích hoạt tạo kết nối RDT/UDP khi truyền dữ liệu

=== XOÁ FILE NÀY THÌ GỊ HỎNG? ===
  - Server không thể khởi chạy, không tiếp nhận được bất kỳ client nào kết nối tới.
"""

import socket
import threading
import sys
import os
import itertools
import time

# Đảm bảo import được module common
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lock dùng chung để in log không bị đè chữ giữa các thread
log_lock = threading.Lock()


def safe_log(msg: str):
    """Ghi log an toàn giữa các luồng (Thread-safe logging)."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    with log_lock:
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            printable = line.encode(encoding, errors="replace").decode(encoding)
            print(printable, flush=True)


def _redact_command(command: str) -> str:
    """Ẩn credential trước khi ghi command vào server log."""
    verb, separator, _argument = command.partition(" ")
    if separator and verb.upper() == "PASS":
        return f"{verb} ********"
    return command


class ClientHandler(threading.Thread):
    """
    Luồng xử lý riêng cho từng Client kết nối (Per-client thread).

    Mỗi client kết nối tới server sẽ có 1 instance của ClientHandler chạy độc lập.
    """

    def __init__(self, client_socket: socket.socket, client_address: tuple, server: 'FTPServer'):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.server = server
        self.is_running = True
        self.daemon = True  # Thread tự đóng khi main program thoát
        self.session_id = server.next_session_id()
        self.connected_at = time.time()
        self._cleanup_lock = threading.Lock()
        self._cleaned_up = False

    def run(self):
        """Vòng lặp nhận và xử lý lệnh từ Client (TCP Control Channel)."""
        safe_log(
            f"[+] [{self.session_id}] Client mới kết nối từ: "
            f"{self.client_address[0]}:{self.client_address[1]}"
        )
        
        # Set timeout 0.5s để recv không bị block mãi mãi
        self.client_socket.settimeout(0.5)

        try:
            # Gửi mã chào mừng 220 Service Ready chuẩn FTP khi mới kết nối
            self.send_response("220 Hybrid FTP Server Ready\r\n")

            while self.is_running:
                try:
                    # Nhận dữ liệu lệnh từ TCP Control Channel (buffer 1024 bytes)
                    data = self.client_socket.recv(1024)
                    if not data:
                        # Client chủ động đóng kết nối (EOF)
                        break
                except socket.timeout:
                    continue

                # Decode văn bản lệnh gửi lên
                command_raw = data.decode('utf-8', errors='replace').strip()
                if not command_raw:
                    continue

                safe_log(
                    f"[{self.session_id}] "
                    f"[{self.client_address[0]}:{self.client_address[1]}] "
                    f"Command: {_redact_command(command_raw)}"
                )

                # TUẦN 1: Echo mode test đơn giản / Xử lý lệnh QUIT cơ bản
                if command_raw.upper() == "QUIT":
                    self.send_response("221 Goodbye.\r\n")
                    break
                else:
                    # Phản hồi dạng Echo để test đa luồng ở Tuần 1
                    self.send_response(f"200 ECHO: {command_raw}\r\n")

        except (ConnectionResetError, BrokenPipeError):
            safe_log(
                f"[-] [{self.session_id}] Client {self.client_address} "
                "ngắt kết nối đột ngột."
            )
        except Exception as e:
            safe_log(
                f"[!] [{self.session_id}] Lỗi xử lý client "
                f"{self.client_address}: {e}"
            )
        finally:
            self.cleanup()

    def send_response(self, response_str: str):
        """Gửi phản hồi text về cho client qua TCP Control channel."""
        try:
            self.client_socket.sendall(response_str.encode('utf-8'))
        except Exception as e:
            safe_log(f"[!] Lỗi khi gửi response tới {self.client_address}: {e}")

    def cleanup(self):
        """Dọn dẹp tài nguyên khi Client ngắt kết nối."""
        with self._cleanup_lock:
            if self._cleaned_up:
                return
            self._cleaned_up = True
            self.is_running = False
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.client_socket.close()
            except OSError:
                pass
        self.server.unregister_client(self)
        safe_log(
            f"[-] [{self.session_id}] Đã đóng kết nối với "
            f"{self.client_address[0]}:{self.client_address[1]}"
        )


class FTPServer:
    """
    Class quản lý Server đa luồng chính.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 2121):
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False
        self.active_clients = []
        self.clients_lock = threading.Lock()
        self._session_ids = itertools.count(1)
        self._session_id_lock = threading.Lock()

    def start(self):
        """Khởi chạy TCP Server và bắt đầu lắng nghe kết nối."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # SO_REUSEADDR cho phép bind lại port ngay lập tức mà không bị chờ TIME_WAIT
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(0.5)  # Thêm timeout 0.5s để accept() không bị treo vĩnh viễn khi stop()
            self.is_running = True
            safe_log(f"[*] FTP Server đang lắng nghe trên {self.host}:{self.port}...")

            while self.is_running:
                try:
                    # Chờ client kết nối (Timeout sau 0.5s để rà soát self.is_running)
                    client_sock, client_addr = self.server_socket.accept()
                    client_sock.settimeout(None)  # Reset timeout trên client socket mới ngắt kết nối
                    
                    # Tạo và chạy Thread xử lý cho Client mới
                    handler = ClientHandler(client_sock, client_addr, self)
                    # Đăng ký trước khi start để stop() không bỏ sót thread vừa tạo.
                    self.register_client(handler)
                    handler.start()
                except socket.timeout:
                    continue
                except OSError:
                    # Bắt lỗi khi server_socket bị đóng bởi lệnh stop()
                    break

        except Exception as e:
            safe_log(f"[!] Lỗi khởi chạy Server: {e}")
        finally:
            self.stop()

    def stop(self):
        """Dừng server và dọn dẹp kết nối."""
        if not self.is_running and not self.server_socket:
            return

        self.is_running = False
        safe_log("[*] Đang dừng Server...")

        # Đóng server socket trước để unblock accept loop
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        # Chụp snapshot rồi nhả lock trước khi cleanup(). cleanup() gọi lại
        # unregister_client(), nên giữ clients_lock ở đây sẽ gây deadlock.
        with self.clients_lock:
            clients = list(self.active_clients)

        for client in clients:
            client.cleanup()

        current_thread = threading.current_thread()
        for client in clients:
            if client is not current_thread and client.is_alive():
                client.join(timeout=1.0)

        safe_log("[*] Server đã dừng hoàn toàn.")

    def register_client(self, client_handler: ClientHandler):
        """Đăng ký client vào danh sách đang hoạt động (Thread-safe)."""
        with self.clients_lock:
            self.active_clients.append(client_handler)

    def unregister_client(self, client_handler: ClientHandler):
        """Xoá client khỏi danh sách đang hoạt động (Thread-safe)."""
        with self.clients_lock:
            if client_handler in self.active_clients:
                self.active_clients.remove(client_handler)

    def get_active_client_count(self) -> int:
        """Lấy số lượng client đang kết nối đồng thời."""
        with self.clients_lock:
            return len(self.active_clients)

    def next_session_id(self) -> str:
        """Cấp session ID duy nhất để log và theo dõi client."""
        with self._session_id_lock:
            return f"S{next(self._session_ids):06d}"

    def get_active_sessions(self) -> list[dict]:
        """Trả snapshot an toàn của bảng session đang hoạt động."""
        with self.clients_lock:
            return [
                {
                    "session_id": client.session_id,
                    "client_ip": client.client_address[0],
                    "client_port": client.client_address[1],
                    "connected_at": client.connected_at,
                    "alive": client.is_alive(),
                }
                for client in self.active_clients
            ]


if __name__ == "__main__":
    # Test chạy thử server từ terminal
    server = FTPServer(host="127.0.0.1", port=2121)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[!] Bị ngắt bởi người dùng (Ctrl+C).")
        server.stop()
