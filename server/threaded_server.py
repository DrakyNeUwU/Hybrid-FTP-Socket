import socket
import threading
import sys
import os
import itertools
import time


from client_handler import ClientHandler



sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)



log_lock = threading.Lock()



def safe_log(msg):

    timestamp = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = f"[{timestamp}] {msg}"


    with log_lock:

        print(
            line,
            flush=True
        )



def _redact_command(command):

    verb, separator, _ = command.partition(" ")


    if separator and verb.upper()=="PASS":

        return f"{verb} ********"


    return command





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
        port=2121
    ):

        self.host = host
        self.port = port


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






if __name__=="__main__":


    server = FTPServer(
        host="127.0.0.1",
        port=2121
    )


    try:

        server.start()


    except KeyboardInterrupt:

        server.stop()