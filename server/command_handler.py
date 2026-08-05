import os
import uuid
import socket
from common.rdt_sender import send_file_rdt
from common.rdt_receiver import receive_file_rdt

class FTPServerSession:
    def __init__(self, control_socket, storage_dir="./server/storage"):
        self.control_socket = control_socket
        self.storage_dir = storage_dir
        self.mode = "PASV"  
        self.pasv_udp_socket = None
        self.client_data_addr = None 

        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def process_command(self, cmd_line):
        cmd, *args = cmd_line.strip().split(" ", 1)
        cmd = cmd.upper()
        arg = args[0] if args else ""

        if cmd == "PASV":
            self.handle_pasv()
        elif cmd == "PORT":
            self.handle_port(arg)
        elif cmd == "RETR":
            self.handle_retr(arg)
        elif cmd == "STOR":
            self.handle_stor(arg)
        elif cmd == "APPE":
            self.handle_appe(arg)
        elif cmd == "STOU":
            self.handle_stou()

    def handle_pasv(self):
        self.mode = "PASV"
        self.pasv_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pasv_udp_socket.bind(('127.0.0.1', 0)) 
        port = self.pasv_udp_socket.getsockname()[1]

        p1, p2 = port // 256, port % 256
        res = f"227 Entering Passive Mode (127,0,0,1,{p1},{p2})\r\n"
        self.control_socket.sendall(res.encode())

    def handle_port(self, arg):
        self.mode = "PORT"
        parts = arg.split(',')
        ip = ".".join(parts[:4])
        port = int(parts[4]) * 256 + int(parts[5])
        self.client_data_addr = (ip, port)
        self.control_socket.sendall(b"200 PORT command successful.\r\n")

    def handle_retr(self, filename):
        filepath = os.path.join(self.storage_dir, filename)
        if not os.path.exists(filepath):
            self.control_socket.sendall(b"550 File not found.\r\n")
            return

        self.control_socket.sendall(b"150 Opening Data Connection.\r\n")
        
        target_ip, target_port = ('127.0.0.1', 0)
        if self.mode == "PORT":
            target_ip, target_port = self.client_data_addr

        ok = send_file_rdt(filepath, target_ip, target_port)
        self._cleanup_pasv_socket()
        
        if ok:
            self.control_socket.sendall(b"226 Transfer complete.\r\n")
        else:
            self.control_socket.sendall(b"426 Transfer aborted.\r\n")

    def handle_stor(self, filename, write_mode="wb"):
        filepath = os.path.join(self.storage_dir, filename)
        self.control_socket.sendall(b"150 Opening Data Connection.\r\n")

        ok = receive_file_rdt(self.pasv_udp_socket, filepath, write_mode=write_mode)
        self._cleanup_pasv_socket()

        if ok:
            self.control_socket.sendall(b"226 Transfer complete.\r\n")
        else:
            self.control_socket.sendall(b"426 Transfer aborted.\r\n")

    def handle_appe(self, filename):
        self.handle_stor(filename, write_mode="ab")

    def handle_stou(self):
        unique_name = f"file_{uuid.uuid4().hex[:8]}.dat"
        filepath = os.path.join(self.storage_dir, unique_name)
        
        self.control_socket.sendall(f"150 FILE: {unique_name}\r\n".encode())
        ok = receive_file_rdt(self.pasv_udp_socket, filepath, write_mode="wb")
        self._cleanup_pasv_socket()

        if ok:
            self.control_socket.sendall(b"226 Transfer complete.\r\n")
        else:
            self.control_socket.sendall(b"426 Transfer aborted.\r\n")

    def _cleanup_pasv_socket(self):
        if self.pasv_udp_socket:
            try:
                self.pasv_udp_socket.close()
            except Exception:
                pass
            self.pasv_udp_socket = None