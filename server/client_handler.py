import threading
import socket
import os

from server.command_parser import CommandParser
from server.command_handler import CommandHandler
from server.session import Session
from server.ftp_reply import FTPReply
from server.transfer_manager import TransferManager
from server.rdt_adapter import RDTSenderAdapter, RDTReceiverAdapter
from common.filesystem_service import FilesystemService
from server.logging_utils import redact_command, safe_log

class ClientHandler(threading.Thread):

    def __init__(self, sock: socket.socket, addr, server):
        super().__init__()
        self.socket = sock
        self.addr = addr
        self.server = server
        self.session_id = server.next_session_id() if server else "S000000"

        self.session = Session(ftp_root=getattr(server, "ftp_root", "./ftp_root"))
        self.session.session_id = self.session_id
        self.session.send_reply = self.send
        self.session.peer_ip = addr[0] if (addr and isinstance(addr, tuple)) else None
        try:
            local_address = sock.getsockname() if sock else None
            self.session.server_ip = getattr(server, "advertised_host", None) or (
                local_address[0]
                if isinstance(local_address, tuple) and local_address
                else "127.0.0.1"
            )
        except OSError:
            self.session.server_ip = "127.0.0.1"

        os.makedirs(self.session.ftp_root, exist_ok=True)
        shared_filesystem = getattr(server, "filesystem_service", None)
        self.filesystem_service = shared_filesystem or FilesystemService(
            self.session.ftp_root
        )
        self.sender_adapter = RDTSenderAdapter()
        self.receiver_adapter = RDTReceiverAdapter()
        self.transfer_manager = TransferManager(
            filesystem=self.filesystem_service,
            sender=self.sender_adapter,
            receiver=self.receiver_adapter,
        )

        self.handler = CommandHandler(self.transfer_manager)
        self.buffer = b""

    def run(self):
        try:
            self.send(FTPReply.READY)
            while True:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                self.buffer += data
                while b"\r\n" in self.buffer:
                    line, self.buffer = self.buffer.split(b"\r\n", 1)
                    try:
                        raw_command = line.decode("utf-8")
                    except UnicodeDecodeError:
                        self.send("500 Syntax error, command unrecognized\r\n")
                        continue

                    try:
                        command = CommandParser.parse(raw_command)
                        safe_log(
                            f"Command session={self.session_id} "
                            f"ip={self.session.peer_ip} "
                            f"transfer_id={self.session.transfer_id or '-'} "
                            f"command={redact_command(raw_command)}"
                        )
                        response = self.handler.handle(command, self.session)
                        if response:
                            self.send(response)
                        
                        if command.name == "QUIT":
                            return
                    except Exception as e:
                        self.send("500 Internal server error\r\n")

        except ConnectionResetError:
            pass
        except Exception:
            pass
        finally:
            self.cleanup()

    def send(self, response):
        reply_code = response.split(" ", 1)[0].strip() if response else "-"
        safe_log(
            f"Reply session={self.session_id} ip={self.session.peer_ip} "
            f"transfer_id={self.session.transfer_id or '-'} code={reply_code}"
        )
        try:
            self.socket.sendall(response.encode("utf-8"))
        except OSError:
            pass

    def cleanup(self):
        try:
            self.transfer_manager.cancel(self.session)
        except Exception:
            pass

        worker = getattr(self.session, "transfer_worker", None)
        if worker and worker.is_alive():
            worker.join(timeout=1.0)

        if getattr(self.session, 'data_socket', None):
            try: self.session.data_socket.close()
            except Exception: pass
            self.session.data_socket = None

        self.session.data_host = None
        self.session.data_port = None
        self.session.data_mode = None
        self.session.rename_from = None
        self.session.transfer_cancelled = False
        self.session.current_transfer = None
        self.session.transfer_worker = None

        if self.server:
            try: self.server.unregister_client(self)
            except Exception: pass
        active_count = "-"
        get_active_count = getattr(self.server, "get_active_client_count", None)
        if callable(get_active_count):
            active_count = get_active_count()
        safe_log(
            f"Client disconnected session={self.session_id} "
            f"ip={self.session.peer_ip} "
            f"active={active_count}"
        )
        get_active_sessions = getattr(self.server, "get_active_sessions", None)
        if callable(get_active_sessions):
            safe_log(f"Active sessions={get_active_sessions()}")
        
        try: self.socket.close()
        except Exception: pass
