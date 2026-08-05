import threading
import socket

from command_parser import CommandParser
from command_handler import CommandHandler
from session import Session
from ftp_reply import FTPReply
from transfer_manager import TransferManager


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


        # mỗi client một session riêng
        self.session = Session(
            ftp_root="./ftp_root"
        )


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



    def send(self,response):

        self.socket.sendall(
            response.encode()
        )



    def cleanup(self):

        try:
            self.socket.close()

        except:
            pass



