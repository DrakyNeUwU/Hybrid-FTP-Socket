import os
import hashlib
import socket
import time
from server.ftp_reply import FTPReply


class CommandHandler:

    def __init__(self, transfer_manager=None):
        self.transfer_manager = transfer_manager

    def handle(
        self,
        command,
        session
    ):

        cmd = command.name


        if cmd == "USER":

            return self.user(
                command.argument,
                session
            )

        elif cmd == "HASH":

            return self.hash_cmd(
                command.argument,
                session
            )

        elif cmd == "PASS":

            return self.password(
                command.argument,
                session
            )

        elif cmd == "TYPE":

            return self.type_cmd(
                command.argument,
                session
            )


        elif cmd == "NLST":

            return self.nlst(
                session
            )

        elif cmd == "PWD":

            return self.pwd(
                session
            )


        elif cmd == "QUIT":

            return FTPReply.QUIT
        
        elif cmd == "CWD":

            return self.cwd(
                command.argument,
                session
            )

        elif cmd == "CDUP":

            return self.cdup(
                session
            )
        
        elif cmd == "MKD":

            return self.mkd(
                command.argument,
                session
            )


        elif cmd == "RMD":

            return self.rmd(
                command.argument,
                session
            )
        elif cmd == "RETR":

            return self.retr(
                command.argument,
                session
            )


        elif cmd == "STOR":

            return self.stor(
                command.argument,
                session
            )


        elif cmd == "STOU":

            return self.stou(
                command.argument,
                session
            )


        elif cmd == "APPE":

            return self.appe(
                command.argument,
                session
            )   
        elif cmd == "ABOR":

            return self.abor(
                session
            )

        elif cmd == "DELE":

            return self.dele(
                command.argument,
                session
            )
        
        elif cmd == "PORT":

            return self.port_cmd(
                command.argument,
                session
            )
        
        elif cmd == "PASV":

            return self.pasv(
                session
            )

        elif cmd == "RNFR":

            return self.rnfr(
                command.argument,
                session
            )


        elif cmd == "RNTO":

            return self.rnto(
                command.argument,
                session
            )

        elif cmd == "LIST":

            return self.list_dir(
                command.argument,
                session
            )

        elif cmd == "MODE":

            return self.mode_cmd(
                command.argument,
                session
            )


        elif cmd == "NLST":

            return self.nlst(
                command.argument,
                session
            )

        elif cmd == "SIZE":

            return self.size_cmd(
                command.argument,
                session
            )

        elif cmd == "MDTM":

            return self.mdtm_cmd(
                command.argument,
                session
            )

        elif cmd == "STAT":

            return self.stat_cmd(
                command.argument,
                session
            )

        elif cmd == "NOOP":
            return "200 NOOP OK\r\n"

        elif cmd == "HELP":
            return "214-Supported commands:\r\n USER PASS QUIT NOOP PWD CWD CDUP MKD RMD LIST NLST STAT SIZE MDTM TYPE MODE HELP PORT PASV RETR STOR STOU APPE DELE RNFR RNTO HASH ABOR\r\n214 Help OK\r\n"

        elif cmd == "HELLO" or cmd.startswith("TEST_MSG_") or cmd == "ECHO":
            arg_str = f" {command.argument}" if command.argument else ""
            return f"200 ECHO: {cmd}{arg_str}\r\n"

        else:

            return FTPReply.NOT_IMPLEMENTED



    def pwd(
        self,
        session
    ):

        if not session.is_logged_in:

            return (
                "530 Not logged in\r\n"
            )


        return (
            f'257 "{session.current_dir}"\r\n'
        )

    def pasv(
        self,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        udp_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )


        udp_socket.bind(
            ("0.0.0.0",0)
        )
        session.data_socket = udp_socket

        port = udp_socket.getsockname()[1]


        session.data_host = "127.0.0.1"
        session.data_port = port
        session.data_mode = "PASSIVE"


        p1 = port // 256
        p2 = port % 256


        return (
            f"227 Entering Passive Mode "
            f"(127,0,0,1,{p1},{p2})\r\n"
        )

    def appe(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        if arg == "":

            return "501 Missing filename\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        session.current_transfer = {
            "type": "APPE",
            "file": path
        }


        return (
            "150 Ready for append\r\n"
        )

    def stou(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        filename = "upload_001"


        path = os.path.join(
            session.current_dir,
            filename
        )


        session.current_transfer = {
            "type": "STOU",
            "file": path
        }


        return (
            f"150 Opening transfer {filename}\r\n"
        )

    def stor(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        if arg == "":

            return "501 Missing filename\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        session.current_transfer = {
            "type": "STOR",
            "file": path
        }


        result = self.transfer_manager.upload(
            session,
            path
        )


        if result:

            return "226 Transfer complete\r\n"


        return "426 Transfer failed\r\n"

    def retr(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        if arg == "":

            return "501 Missing filename\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        if not os.path.isfile(path):

            return "550 File not found\r\n"


        session.current_transfer = {
            "type": "RETR",
            "file": path
        }


        # sau này gọi Role B ở đây

        result = self.transfer_manager.download(
            session,
            path
        )


        if result:

            return "226 Transfer complete\r\n"


        return "426 Transfer failed\r\n"

    def abor(
        self,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        session.transfer_cancelled = True


        return "226 Abort successful\r\n"


    def hash_cmd(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        if arg == "":

            return "501 Missing filename\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        if not os.path.isfile(path):

            return "550 File not found\r\n"


        try:

            sha256 = hashlib.sha256()


            with open(path, "rb") as f:

                while True:

                    data = f.read(4096)

                    if not data:
                        break

                    sha256.update(data)


            return (
                f"213 SHA256 {sha256.hexdigest()}\r\n"
            )


        except:

            return "550 HASH failed\r\n"


    def port_cmd(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        try:

            parts = arg.split(",")


            if len(parts) != 6:

                return "501 Invalid PORT\r\n"


            ip = ".".join(parts[:4])


            port = (
                int(parts[4]) * 256
                +
                int(parts[5])
            )


            session.data_host = ip
            session.data_port = port
            session.data_mode = "ACTIVE"


            return "200 PORT command successful\r\n"


        except:

            return "501 Invalid PORT\r\n"
            

    def type_cmd(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        arg = arg.upper()


        if arg == "A":

            session.transfer_type = "A"

            return "200 Type set to ASCII\r\n"



        elif arg == "I":

            session.transfer_type = "I"

            return "200 Type set to Binary\r\n"



        else:

            return "501 Invalid TYPE\r\n"

    def mode_cmd(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        arg = arg.upper()


        if arg == "S":

            session.transfer_mode = "S"

            return "200 Mode Stream\r\n"


        elif arg in ["B", "C"]:

            return "502 Mode not implemented\r\n"


        else:

            return "501 Invalid MODE\r\n"


    def cwd(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return (
                "530 Not logged in\r\n"
            )


        if arg == "":

            return (
                "501 Missing directory\r\n"
            )


        new_path = os.path.abspath(
            os.path.join(
                session.current_dir,
                arg
            )
        )

        if not new_path.startswith(session.ftp_root):
            return (
                "550 Cannot go above FTP root\r\n"
            )

        if os.path.isdir(new_path):

            session.current_dir = os.path.abspath(
                new_path
            )

            return (
                "250 Directory changed\r\n"
            )


        return (
            "550 Directory not found\r\n"
        )

    def rnto(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        if session.rename_from is None:

            return "503 RNFR required\r\n"


        new_path = os.path.join(
            session.current_dir,
            arg
        )


        try:

            os.rename(
                session.rename_from,
                new_path
            )

            session.rename_from = None

            return "250 Rename successful\r\n"


        except:

            return "550 Rename failed\r\n"
    def rnfr(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        if arg == "":

            return "501 Missing filename\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        if os.path.exists(path):

            session.rename_from = path

            return "350 Ready for RNTO\r\n"


        return "550 File not found\r\n"

    def nlst(
        self,
        session
    ):

        if not session.is_logged_in:

            return "530 Not logged in\r\n"


        try:

            files = os.listdir(
                session.current_dir
            )


            return (
                "\r\n".join(files)
                +
                "\r\n"
            )


        except:

            return "550 Cannot list\r\n"

    def cdup(
        self,
        session
    ):

        if not session.is_logged_in:

            return (
                "530 Not logged in\r\n"
            )


        parent = os.path.dirname(
            session.current_dir
        )


        if parent.startswith(session.ftp_root):

            session.current_dir = parent

            return (
                "200 Directory changed to parent\r\n"
            )


        return (
            "550 Cannot go above FTP root\r\n"
        ) 

    def user(
        self,
        arg,
        session
    ):
        if not arg or not arg.strip():
            return "501 Invalid username\r\n"
        session.username = arg.strip()
        return FTPReply.USER_OK

    def nlst(
        self,
        arg,
        session
    ):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"

        target = os.path.abspath(os.path.join(session.current_dir, arg)) if arg else session.current_dir
        if not target.startswith(session.ftp_root) or not os.path.exists(target):
            return "550 Cannot list directory\r\n"

        try:
            if os.path.isdir(target):
                files = os.listdir(target)
            else:
                files = [os.path.basename(target)]
            return "\r\n".join(files) + "\r\n"
        except:
            return "550 Cannot list directory\r\n"

    def list_dir(
        self,
        arg,
        session
    ):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"

        target = os.path.abspath(os.path.join(session.current_dir, arg)) if arg else session.current_dir
        if not target.startswith(session.ftp_root) or not os.path.exists(target):
            return "550 Cannot list directory\r\n"

        try:
            if os.path.isdir(target):
                files = os.listdir(target)
            else:
                files = [os.path.basename(target)]
            result = "\r\n".join(files)
            return result + "\r\n226 Transfer complete\r\n"
        except:
            return "550 Cannot list directory\r\n"

    def size_cmd(
        self,
        arg,
        session
    ):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        path = os.path.abspath(os.path.join(session.current_dir, arg))
        if not path.startswith(session.ftp_root) or not os.path.isfile(path):
            return "550 File not found\r\n"
        return f"213 {os.path.getsize(path)}\r\n"

    def mdtm_cmd(
        self,
        arg,
        session
    ):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        path = os.path.abspath(os.path.join(session.current_dir, arg))
        if not path.startswith(session.ftp_root) or not os.path.isfile(path):
            return "550 File not found\r\n"
        mtime = os.path.getmtime(path)
        formatted_time = time.strftime("%Y%m%d%H%M%S", time.gmtime(mtime))
        return f"213 {formatted_time}\r\n"

    def stat_cmd(
        self,
        arg,
        session
    ):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return f"211-FTP Server Status:\r\n Logged in as: {session.username}\r\n TYPE: {session.transfer_type}, MODE: {session.transfer_mode}\r\n211 End of status\r\n"
        path = os.path.abspath(os.path.join(session.current_dir, arg))
        if not path.startswith(session.ftp_root) or not os.path.exists(path):
            return "550 File or directory not found\r\n"
        if os.path.isdir(path):
            files = os.listdir(path)
            lines = "\r\n".join(files)
            return f"212-Directory status:\r\n{lines}\r\n212 End of status\r\n"
        else:
            size = os.path.getsize(path)
            return f"213-File status: {arg}\r\n Size: {size} bytes\r\n213 End of status\r\n"
    def dele(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:
            return "530 Not logged in\r\n"


        if arg == "":
            return "501 Missing filename\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        try:

            os.remove(path)

            return (
                "250 File deleted\r\n"
            )


        except:

            return (
                "550 File not found\r\n"
            )
    def rmd(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:
            return "530 Not logged in\r\n"


        if arg == "":
            return "501 Missing directory name\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        try:

            os.rmdir(path)

            return (
                "250 Directory removed\r\n"
            )


        except:

            return (
                "550 Cannot remove directory\r\n"
            )

    def mkd(
        self,
        arg,
        session
    ):

        if not session.is_logged_in:
            return "530 Not logged in\r\n"


        if arg == "":
            return "501 Missing directory name\r\n"


        path = os.path.join(
            session.current_dir,
            arg
        )


        try:

            os.mkdir(path)

            return (
                "257 Directory created\r\n"
            )

        except FileExistsError:

            return (
                "550 Directory already exists\r\n"
            )

        except:

            return (
                "550 Cannot create directory\r\n"
            )

    def password(
        self,
        arg,
        session
    ):

        if session.username is None:

            return (
                "503 Login with USER first\r\n"
            )


        if arg == "123456":

            session.is_logged_in = True

            return FTPReply.LOGIN_OK


        return (
            "530 Login incorrect\r\n"
        )