import threading
import socket

from server.command_parser import CommandParser
from server.command_handler import CommandHandler
from server.session import Session
from server.ftp_reply import FTPReply
from server.transfer_manager import TransferManager


class ClientHandler(threading.Thread):

    def __init__(
        self,
        sock: socket.socket,
        addr,
        server
    ):

        super().__init__()

        self.socket = sock
        self.addr = addr
        self.server = server
        self.session_id = server.next_session_id() if server else "S000000"

        # mỗi client một session riêng
        self.session = Session(
            ftp_root="./ftp_root"
        )
        self.session.session_id = self.session_id

        self.transfer_manager = TransferManager()

        self.handler = CommandHandler(
            self.transfer_manager
        )

    def run(self):

        try:

            self.send(
                FTPReply.READY
            )


            while True:

                data = self.socket.recv(1024)


                if not data:
                    break



                raw_command = data.decode(
                    "utf-8",
                    errors="replace"
                )


                command = CommandParser.parse(
                    raw_command
                )


                response = self.handler.handle(
                    command,
                    self.session
                )


                self.send(response)


                # Nếu client gửi QUIT thì đóng session
                if command.name == "QUIT":
                    break

        except ConnectionResetError:

            pass

        finally:

            self.cleanup()

    def send(self, response):
        try:
            self.socket.sendall(
                response.encode()
            )
        except OSError:
            pass

    def cleanup(self):
        if self.server:
            try:
                self.server.unregister_client(self)
            except:
                pass
        try:
            self.socket.close()
        except:
            pass



