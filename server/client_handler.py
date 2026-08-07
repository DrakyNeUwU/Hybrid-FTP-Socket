import threading
import socket
import os

from server.command_parser import CommandParser
from server.command_handler import CommandHandler
from server.session import Session
from server.ftp_reply import FTPReply
from server.transfer_manager import TransferManager
from common.filesystem_service import FilesystemService

class ClientHandler(threading.Thread):

    def __init__(self, sock: socket.socket, addr, server):
        super().__init__()
        self.socket = sock
        self.addr = addr
        self.server = server
        self.session_id = server.next_session_id() if server else "S000000"

        self.session = Session(ftp_root="./ftp_root")
        self.session.session_id = self.session_id
        self.session.send_reply = self.send

        os.makedirs(self.session.ftp_root, exist_ok=True)
        self.filesystem_service = FilesystemService(self.session.ftp_root)
        self.transfer_manager = TransferManager(filesystem=self.filesystem_service)

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
        try:
            self.socket.sendall(response.encode("utf-8"))
        except OSError:
            pass

    def cleanup(self):
        try:
            self.transfer_manager.cancel(self.session)
        except:
            pass

        if getattr(self.session, 'data_socket', None):
            try: self.session.data_socket.close()
            except: pass
            self.session.data_socket = None

        self.session.data_host = None
        self.session.data_port = None
        self.session.data_mode = None
        self.session.rename_from = None
        self.session.transfer_cancelled = False
        self.session.current_transfer = None

        if self.server:
            try: self.server.unregister_client(self)
            except: pass
        
        try: self.socket.close()
        except: pass
