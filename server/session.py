import os
class Session:

    def __init__(self, ftp_root="./ftp_root"):

        self.username = None
        self.is_logged_in = False

        self.ftp_root = os.path.abspath(ftp_root)
        self.current_dir = self.ftp_root

        self.rename_from = None

        # thêm
        self.transfer_type = "I"   # mặc định binary
        self.transfer_mode = "S"   # mặc định stream
        self.data_host = None
        self.data_port = None
        self.data_socket = None
        self.data_mode = None
        self.transfer_cancelled = False
        self.current_transfer = None