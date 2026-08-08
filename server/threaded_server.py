import argparse
import socket
import threading
import sys
import os
import itertools
import time


from server.client_handler import ClientHandler
from server.logging_utils import redact_command as _redact_command, safe_log






class FTPServer:
    """
    TCP Control Server.
    
    Nhiệm vụ:
    - listen TCP
    - accept client
    - tạo ClientHandler thread
    - quản lý session
    """



    def __init__(
        self,
        host="0.0.0.0",
        port=2121,
        ftp_root="./ftp_root",
        advertised_host=None,
    ):

        self.host = host
        self.port = port
        self.ftp_root = ftp_root
        self.advertised_host = advertised_host


        self.server_socket = None


        self.is_running = False


        # danh sách client đang kết nối

        self.active_clients = []


        self.clients_lock = threading.Lock()



        # tạo session id

        self._session_ids = itertools.count(1)


        self._session_id_lock = threading.Lock()




    def start(self):

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )


        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )



        self.server_socket.bind(
            (
                self.host,
                self.port
            )
        )

        self.port = self.server_socket.getsockname()[1]


        self.server_socket.listen(5)


        self.server_socket.settimeout(
            0.5
        )


        self.is_running=True


        safe_log(
            f"FTP Server listen {self.host}:{self.port}"
        )



        while self.is_running:


            try:

                client_sock, client_addr = (
                    self.server_socket.accept()
                )


                handler = ClientHandler(
                    client_sock,
                    client_addr,
                    self
                )


                self.register_client(
                    handler
                )

                safe_log(
                    f"Client connected session={handler.session_id} "
                    f"ip={client_addr[0]}:{client_addr[1]} "
                    f"active={self.get_active_client_count()}"
                )
                safe_log(f"Active sessions={self.get_active_sessions()}")


                handler.start()



            except socket.timeout:

                continue



            except OSError:

                break



        self.stop()






    def stop(self):

        self.is_running=False


        safe_log(
            "Stopping server..."
        )



        if self.server_socket:

            try:

                self.server_socket.close()

            except:

                pass



        with self.clients_lock:

            clients = list(
                self.active_clients
            )



        for client in clients:

            client.cleanup()





    def register_client(
        self,
        client_handler
    ):


        with self.clients_lock:

            self.active_clients.append(
                client_handler
            )





    def unregister_client(
        self,
        client_handler
    ):


        with self.clients_lock:

            if client_handler in self.active_clients:

                self.active_clients.remove(
                    client_handler
                )





    def next_session_id(self):

        with self._session_id_lock:

            return (
                f"S{next(self._session_ids):06d}"
            )





    def get_active_client_count(self):
        with self.clients_lock:
            return len(self.active_clients)

    def get_active_sessions(self):

        with self.clients_lock:

            return [

                {
                    "session_id":
                        c.session_id,

                    "ip":
                        c.addr[0],

                    "port":
                        c.addr[1],

                    "alive":
                        c.is_alive()
                }

                for c in self.active_clients

            ]






def main(argv=None):
    """Start the FTP server with optional LAN-friendly endpoint settings."""

    parser = argparse.ArgumentParser(description="Hybrid FTP TCP control server")
    parser.add_argument("--host", default="127.0.0.1", help="TCP bind address")
    parser.add_argument("--port", type=int, default=2121, help="TCP control port")
    parser.add_argument("--ftp-root", default="./ftp_root", help="FTP root directory")
    parser.add_argument(
        "--advertise-host",
        default=None,
        help="IP address advertised in PASV replies; required when binding 0.0.0.0 for LAN clients",
    )
    args = parser.parse_args(argv)
    server = FTPServer(
        host=args.host,
        port=args.port,
        ftp_root=args.ftp_root,
        advertised_host=args.advertise_host,
    )
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
