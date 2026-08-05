import os
import socket
from common.rdt_sender import send_file_rdt
from common.rdt_receiver import receive_file_rdt
from common.rdt_utils import parse_pasv_response, format_port_command

class FTPClient:
    def __init__(self, server_ip='127.0.0.1', control_port=21):
        self.server_ip = server_ip
        self.control_port = control_port
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.download_dir = "./client/downloads"

        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def connect(self):
        self.control_socket.connect((self.server_ip, self.control_port))

    def enter_pasv(self):
        self.control_socket.sendall(b"PASV\r\n")
        res = self.control_socket.recv(1024).decode()
        return parse_pasv_response(res)  

    def enter_port(self):
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data_sock.bind(('127.0.0.1', 0))
        local_port = data_sock.getsockname()[1]
        
        port_cmd = format_port_command('127.0.0.1', local_port)
        self.control_socket.sendall(port_cmd.encode())
        res = self.control_socket.recv(1024).decode()
        return data_sock

    def download_file(self, remote_filename):
        """Lệnh RETR: Tải file về Client"""
        srv_ip, srv_port = self.enter_pasv()
        
        self.control_socket.sendall(f"RETR {remote_filename}\r\n".encode())
        status = self.control_socket.recv(1024).decode()
        
        if status.startswith("150"):
            dst_path = os.path.join(self.download_dir, remote_filename)
            rec_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ok = receive_file_rdt(rec_socket, dst_path)
            
            complete_res = self.control_socket.recv(1024).decode()
            print("Download finish:", complete_res.strip())

    def upload_file(self, local_filepath, remote_filename, cmd="STOR"):
        """Lệnh STOR / APPE: Đẩy file từ Client lên Server"""
        srv_ip, srv_port = self.enter_pasv()

        self.control_socket.sendall(f"{cmd} {remote_filename}\r\n".encode())
        status = self.control_socket.recv(1024).decode()

        if status.startswith("150"):
            ok = send_file_rdt(local_filepath, srv_ip, srv_port)
            complete_res = self.control_socket.recv(1024).decode()
            print(f"{cmd} finish:", complete_res.strip())

    def upload_unique_file(self, local_filepath):
        """Lệnh STOU: Đẩy file lên với tên ngẫu nhiên"""
        srv_ip, srv_port = self.enter_pasv()

        self.control_socket.sendall(b"STOU\r\n")
        status = self.control_socket.recv(1024).decode()

        if status.startswith("150"):
            ok = send_file_rdt(local_filepath, srv_ip, srv_port)
            complete_res = self.control_socket.recv(1024).decode()
            print("STOU finish:", complete_res.strip())