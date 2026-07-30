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

# Đảm bảo import được module common
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lock dùng chung để in log không bị đè chữ giữa các thread
log_lock = threading.Lock()


def safe_log(msg: str):
    """Ghi log an toàn giữa các luồng (Thread-safe logging)."""
    with log_lock:
        print(msg, flush=True)

def parse_command(command_raw: str):
    """
    Tách chuỗi lệnh thành command và argument.
    Ví dụ:
        USER admin
    =>
        command = USER
        argument = admin
    """
    parts = command_raw.split(maxsplit=1)

    command = parts[0].upper()
    argument = parts[1] if len(parts) > 1 else ""

    return command, argument

class Session:
    """
    Quản lý trạng thái của từng client.
    """

    def __init__(self):
        self.username = None
        self.is_logged_in = False
        self.current_dir = os.getcwd()

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
        self.session = Session()
        self.is_running = True
        self.daemon = True  # Thread tự đóng khi main program thoát

    def run(self):
        """Vòng lặp nhận và xử lý lệnh từ Client (TCP Control Channel)."""
        safe_log(f"[+] Client mới kết nối từ: {self.client_address[0]}:{self.client_address[1]}")
        
        # Thêm client vào danh sách quản lý của server
        self.server.register_client(self)

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

                safe_log(f"[{self.client_address[0]}:{self.client_address[1]}] Command: {command_raw}")

                command, argument = parse_command(command_raw)

                if command == "USER":
                    if argument == "admin":
                        self.session.username = argument
                        self.send_response("331 Username OK, need password\r\n")
                    else:
                        self.send_response("530 Invalid username\r\n")

                elif command == "PASS":

                    if self.session.username != "admin":
                        self.send_response("503 Login with USER first\r\n")

                    elif argument == "123456":
                        self.session.is_logged_in = True
                        self.send_response("230 Login successful\r\n")

                    else:
                        self.send_response("530 Login incorrect\r\n")
                elif command == "NOOP":

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    else:
                        self.send_response("200 OK\r\n")
                elif command == "PWD":

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    else:
                        self.send_response(f'257 "{self.session.current_dir}"\r\n')
                
                elif command == "CWD":

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    elif argument == "":
                        self.send_response("550 Directory not found\r\n")

                    elif os.path.isdir(argument):
                        self.session.current_dir = os.path.abspath(argument)
                        self.send_response("250 Directory changed\r\n")

                    else:
                        self.send_response("550 Directory not found\r\n")
                
                elif command == "LIST":

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    else:
                        files = os.listdir(self.session.current_dir)

                        if files:
                            self.send_response("\n".join(files) + "\r\n226 Transfer complete\r\n")
                        else:
                            self.send_response("226 Directory is empty\r\n")
                
                elif command == "MKD":

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    elif argument == "":
                        self.send_response("550 Missing directory name\r\n")

                    else:
                        try:
                            path = os.path.join(self.session.current_dir, argument)
                            os.mkdir(path)
                            self.send_response("257 Directory created\r\n")
                        except:
                            self.send_response("550 Cannot create directory\r\n")
                elif command == "RMD":

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    elif argument == "":
                        self.send_response("550 Missing directory name\r\n")

                    else:
                        try:
                            path = os.path.join(self.session.current_dir, argument)
                            os.rmdir(path)
                            self.send_response("250 Directory removed\r\n")
                        except:
                            self.send_response("550 Cannot remove directory\r\n")

                elif command == "DELE":

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    elif argument == "":
                        self.send_response("550 Missing filename\r\n")

                    else:
                        try:
                            path = os.path.join(self.session.current_dir, argument)
                            os.remove(path)
                            self.send_response("250 File deleted\r\n")
                        except:
                            self.send_response("550 File not found\r\n")
                elif command == "QUIT":
                    self.send_response("221 Goodbye.\r\n")
                    break

                else:

                    if not self.session.is_logged_in:
                        self.send_response("530 Not logged in\r\n")

                    else:
                        self.send_response("502 Command not implemented\r\n")
        except (ConnectionResetError, BrokenPipeError):
            safe_log(f"[-] Client {self.client_address} ngắt kết nối đột ngột.")
        except Exception as e:
            safe_log(f"[!] Lỗi xử lý client {self.client_address}: {e}")
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
        self.is_running = False
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.client_socket.close()
        except Exception:
            pass
        self.server.unregister_client(self)
        safe_log(f"[-] Đã đóng kết nối với {self.client_address[0]}:{self.client_address[1]}")


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

        # Đóng tất cả luồng client đang kết nối
        with self.clients_lock:
            for client in list(self.active_clients):
                client.cleanup()
            self.active_clients.clear()

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


if __name__ == "__main__":
    # Test chạy thử server từ terminal
    server = FTPServer(host="127.0.0.1", port=2121)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[!] Bị ngắt bởi người dùng (Ctrl+C).")
        server.stop()
