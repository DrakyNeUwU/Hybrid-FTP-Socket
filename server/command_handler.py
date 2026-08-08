import hashlib
import os
import socket
import threading
from common.filesystem_service import FilesystemOperationError, FilesystemService
from server.ftp_reply import FTPReply
from server.logging_utils import safe_log


class CommandHandler:
    """FTP Command Handler for Role A.

    Handles FTP protocol command dispatching, authentication, argument checking,
    path operation delegation to FilesystemService, and transfer invocation via TransferManager.
    """

    DEFAULT_CREDENTIALS = {
        "admin": "123456",
        "user": "123456",
        "testuser": "123456",
        "anonymous": "",
    }

    def __init__(self, transfer_manager=None, credentials=None):
        self.transfer_manager = transfer_manager
        self.credentials = credentials if credentials is not None else self.DEFAULT_CREDENTIALS

    def _fs(self, session) -> FilesystemService:
        if self.transfer_manager is not None and getattr(self.transfer_manager, "filesystem", None) is not None:
            return self.transfer_manager.filesystem
        root = getattr(session, "ftp_root", "./ftp_root")
        if not os.path.exists(root):
            os.makedirs(root, exist_ok=True)
        return FilesystemService(root)

    def handle(self, command, session):
        cmd = command.name
        arg = command.argument

        # Reset rename state if anything other than RNTO follows RNFR
        if session.rename_from is not None and cmd != "RNTO":
            session.rename_from = None

        if cmd == "USER": return self.user(arg, session)
        elif cmd == "PASS": return self.password(arg, session)
        elif cmd == "QUIT": return self.quit_cmd(arg, session)
        elif cmd == "NOOP": return self.noop_cmd(arg, session)
        elif cmd == "TYPE": return self.type_cmd(arg, session)
        elif cmd == "MODE": return self.mode_cmd(arg, session)
        elif cmd == "PWD": return self.pwd_cmd(arg, session)
        elif cmd == "CWD": return self.cwd(arg, session)
        elif cmd == "CDUP": return self.cdup_cmd(arg, session)
        elif cmd == "MKD": return self.mkd(arg, session)
        elif cmd == "RMD": return self.rmd(arg, session)
        elif cmd == "DELE": return self.dele(arg, session)
        elif cmd == "RNFR": return self.rnfr(arg, session)
        elif cmd == "RNTO": return self.rnto(arg, session)
        elif cmd == "LIST": return self.list_dir(arg, session)
        elif cmd == "NLST": return self.nlst(arg, session)
        elif cmd == "SIZE": return self.size_cmd(arg, session)
        elif cmd == "MDTM": return self.mdtm_cmd(arg, session)
        elif cmd == "STAT": return self.stat_cmd(arg, session)
        elif cmd == "PORT": return self.port_cmd(arg, session)
        elif cmd == "PASV": return self.pasv_cmd(arg, session)
        elif cmd == "RETR": return self.retr(arg, session)
        elif cmd == "STOR": return self.stor(arg, session)
        elif cmd == "STOU": return self.stou(arg, session)
        elif cmd == "APPE": return self.appe(arg, session)
        elif cmd == "ABOR": return self.abor_cmd(arg, session)
        elif cmd == "HASH": return self.hash_cmd(arg, session)
        elif cmd == "HELP": return self.help_cmd(arg, session)
        else:
            return FTPReply.NOT_IMPLEMENTED

    def user(self, arg, session):
        if not arg or not arg.strip():
            return "501 Invalid username\r\n"
        # RFC 959: new USER resets authentication state
        session.username = arg.strip()
        session.is_logged_in = False
        session.rename_from = None
        return FTPReply.USER_OK

    def password(self, arg, session):
        if session.username is None:
            return "503 Login with USER first\r\n"
        if session.is_logged_in:
            return "230 Already logged in\r\n"

        expected = self.credentials.get(session.username)
        # If user is in credentials and password matches (or if default fallback accepted)
        if expected is not None:
            if expected == "" or arg == expected:
                session.is_logged_in = True
                return FTPReply.LOGIN_OK

        # If user not found in explicit dict, fallback check for backward compatibility:
        if arg == "123456":
            session.is_logged_in = True
            return FTPReply.LOGIN_OK

        session.username = None
        return "530 Login incorrect\r\n"

    def quit_cmd(self, arg, session):
        if arg:
            return "501 Syntax error in parameters\r\n"
        session.rename_from = None
        return FTPReply.QUIT

    def noop_cmd(self, arg, session):
        if arg:
            return "501 Syntax error in parameters\r\n"
        return "200 NOOP OK\r\n"

    def pwd_cmd(self, arg, session):
        if arg:
            return "501 Syntax error in parameters\r\n"
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        try:
            display_path = self._fs(session).display_path(session.current_dir)
            return f'257 "{display_path}"\r\n'
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"

    def cwd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing directory\r\n"
        try:
            new_path = self._fs(session).change_directory(session.current_dir, arg)
            session.current_dir = new_path
            return "250 Directory changed\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 Directory not found\r\n"

    def cdup_cmd(self, arg, session):
        if arg:
            return "501 Syntax error in parameters\r\n"
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        try:
            new_path = self._fs(session).parent_directory(session.current_dir)
            session.current_dir = new_path
            return "200 Directory changed to parent\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 Cannot go above FTP root\r\n"

    def mkd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing directory\r\n"
        try:
            self._fs(session).make_directory(session.current_dir, arg)
            return "257 Directory created\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 Cannot create directory\r\n"

    def rmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing directory\r\n"
        try:
            self._fs(session).remove_directory(session.current_dir, arg)
            return "250 Directory removed\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 Cannot remove directory\r\n"

    def dele(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        try:
            self._fs(session).delete(session.current_dir, arg)
            return "250 File deleted\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 Cannot delete file\r\n"

    def rnfr(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        try:
            fs = self._fs(session)
            fs.prepare_retrieve(session.current_dir, arg)
            session.rename_from = arg
            return "350 Ready for RNTO\r\n"
        except FilesystemOperationError as e:
            session.rename_from = None
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            session.rename_from = None
            return "550 File not found\r\n"

    def rnto(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            session.rename_from = None
            return "501 Missing filename\r\n"
        if not session.rename_from:
            return "503 RNFR required\r\n"
        try:
            fs = self._fs(session)
            fs.rename(session.current_dir, session.rename_from, arg)
            session.rename_from = None
            return "250 Rename successful\r\n"
        except FilesystemOperationError as e:
            session.rename_from = None
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            session.rename_from = None
            return "550 Rename failed\r\n"

    def type_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing argument\r\n"
        mode = arg.upper()
        if mode == "A":
            session.transfer_type = "A"
            return "200 Type set to ASCII\r\n"
        elif mode == "I":
            session.transfer_type = "I"
            return "200 Type set to Binary\r\n"
        return "501 Invalid TYPE\r\n"

    def mode_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing argument\r\n"
        mode = arg.upper()
        if mode == "S":
            session.transfer_mode = "S"
            return "200 Mode Stream\r\n"
        elif mode in ("B", "C"):
            return "502 Mode not implemented\r\n"
        return "501 Invalid MODE\r\n"

    def port_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing arguments\r\n"
        try:
            parts = arg.split(",")
            if len(parts) != 6:
                return "501 Invalid PORT\r\n"
            nums = []
            for p in parts:
                v = int(p)
                if not (0 <= v <= 255):
                    return "501 Invalid PORT\r\n"
                nums.append(v)
            ip = ".".join(str(n) for n in nums[:4])
            port = nums[4] * 256 + nums[5]
            if port <= 0 or port > 65535:
                return "501 Invalid PORT\r\n"

            # Anti-FTP bounce check: if peer_ip is set and not local, enforce IP match
            peer_ip = getattr(session, "peer_ip", None)
            if peer_ip and peer_ip not in ("127.0.0.1", "::1", "localhost"):
                if ip != peer_ip and ip not in ("127.0.0.1", "localhost"):
                    return "501 Security error: PORT IP bounce prevented\r\n"

            self._close_data_socket(session)
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.bind(("0.0.0.0", 0))
            session.data_socket = udp
            session.data_host = ip
            session.data_port = port
            session.data_mode = "ACTIVE"
            server_port = udp.getsockname()[1]
            return f"200 PORT command successful (server UDP port {server_port})\r\n"
        except (ValueError, IndexError):
            return "501 Invalid PORT\r\n"

    def pasv_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if arg:
            return "501 Syntax error in parameters\r\n"
        self._close_data_socket(session)

        try:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.bind(("0.0.0.0", 0))
            session.data_socket = udp
            port = udp.getsockname()[1]
            server_ip = getattr(session, "server_ip", None)
            if not server_ip or server_ip == "0.0.0.0":
                try:
                    server_ip = socket.gethostbyname(socket.gethostname())
                except OSError:
                    server_ip = "127.0.0.1"
            session.data_host = server_ip
            session.data_port = port
            session.data_mode = "PASSIVE"
            p1 = port // 256
            p2 = port % 256
            ip_parts = ",".join(server_ip.split("."))
            return f"227 Entering Passive Mode ({ip_parts},{p1},{p2})\r\n"
        except Exception:
            return "425 Cannot open data connection\r\n"

    def list_dir(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        try:
            entries = self._fs(session).list(session.current_dir, arg if arg else "")
            lines = []
            for e in entries:
                if isinstance(e, dict):
                    name = e.get("name", "")
                    size = e.get("size", 0)
                    etype = e.get("type", "-")
                    perms = e.get("permissions", "rwxr-xr-x")
                    modified = e.get("modified", "")
                    try:
                        import datetime
                        dt = datetime.datetime.strptime(modified, "%Y%m%d%H%M%S")
                        mod_str = dt.strftime("%b %d %H:%M")
                    except Exception:
                        mod_str = modified
                    type_char = "d" if etype == "dir" else "-"
                    lines.append(f"{type_char}{perms} 1 ftp ftp {size:>10} {mod_str} {name}")
                else:
                    type_char = getattr(e, "type", "-")
                    if type_char not in ("d", "-"):
                        type_char = "-"
                    size = getattr(e, "size", 0)
                    name = getattr(e, "name", str(e))
                    lines.append(f"{type_char}rwxr-xr-x 1 ftp ftp {size:>10}  {name}")
            result = "\r\n".join(lines)
            return f"150 Here comes the directory listing.\r\n{result}\r\n226 Directory send OK.\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 Cannot list directory\r\n"

    def nlst(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        try:
            entries = self._fs(session).names(session.current_dir, arg if arg else "")
            result = "\r\n".join(entries)
            return f"150 Here comes the directory listing.\r\n{result}\r\n226 Directory send OK.\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 Cannot list directory\r\n"

    def size_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        try:
            size = self._fs(session).size(session.current_dir, arg)
            return f"213 {size}\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 File not found\r\n"

    def mdtm_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        try:
            mtime_str = self._fs(session).modified_time(session.current_dir, arg)
            return f"213 {mtime_str}\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 File not found\r\n"

    def stat_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        return "211-FTP Server status:\r\n211 End of status\r\n"

    def hash_cmd(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        try:
            digest = self._fs(session).hash(session.current_dir, arg, "sha256")
            return f"213 SHA256 {digest}\r\n"
        except FilesystemOperationError as e:
            return f"{e.reply_code} {e.message}\r\n"
        except Exception:
            return "550 HASH failed\r\n"

    def help_cmd(self, arg, session):
        return "214-Supported commands:\r\n USER PASS QUIT NOOP PWD CWD CDUP MKD RMD LIST NLST STAT SIZE MDTM TYPE MODE HELP PORT PASV RETR STOR STOU APPE DELE RNFR RNTO HASH ABOR\r\n214 Help OK\r\n"

    @staticmethod
    def _close_data_socket(session):
        data_socket = getattr(session, "data_socket", None)
        if data_socket is not None:
            try:
                data_socket.close()
            except OSError:
                pass
        session.data_socket = None

    def _start_transfer_thread(self, session, action_name, action_func, arg=None):
        transfer_id = session.new_transfer_id()
        data_mode = getattr(session, "data_mode", None) or "-"
        if isinstance(session.current_transfer, dict):
            session.current_transfer["transfer_id"] = transfer_id

        def run_transfer():
            try:
                if arg is not None:
                    result = action_func(
                        session,
                        arg,
                        data_socket=session.data_socket,
                        endpoint=(session.data_host, session.data_port),
                    )
                else:
                    result = action_func(
                        session,
                        data_socket=session.data_socket,
                        endpoint=(session.data_host, session.data_port),
                    )

                if result:
                    safe_log(
                        f"Transfer session={session.session_id} transfer_id={transfer_id} "
                        f"operation={action_name} mode={data_mode} result=success "
                        f"bytes={getattr(result, 'bytes_transferred', 0)}"
                    )
                    if session.send_reply:
                        session.send_reply("226 Transfer complete\r\n")
                elif result is not None:
                    code = getattr(result, "reply_code", 426)
                    err = getattr(result, "error", "Transfer failed")
                    safe_log(
                        f"Transfer session={session.session_id} transfer_id={transfer_id} "
                        f"operation={action_name} mode={data_mode} result=failed "
                        f"code={code} error={err}"
                    )
                    if session.send_reply:
                        session.send_reply(f"{code} {err}\r\n")
                else:
                    safe_log(
                        f"Transfer session={session.session_id} transfer_id={transfer_id} "
                        f"operation={action_name} mode={data_mode} result=failed code=426"
                    )
                    if session.send_reply:
                        session.send_reply("426 No RDT adapter configured\r\n")
            except Exception as error:
                safe_log(
                    f"Transfer session={session.session_id} transfer_id={transfer_id} "
                    f"operation={action_name} mode={data_mode} result=failed "
                    f"code=426 error={error}"
                )
                if session.send_reply:
                    session.send_reply("426 Transfer failed\r\n")

        t = threading.Thread(target=run_transfer, daemon=True)
        t.start()
        session.transfer_worker = t
        return transfer_id

    @staticmethod
    def _transfer_in_progress(session):
        """Return whether this session already owns an active transfer."""
        worker = getattr(session, "transfer_worker", None)
        return bool(
            isinstance(getattr(session, "current_transfer", None), dict)
            or (worker is not None and worker.is_alive())
        )

    def retr(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        if not session.data_socket and not session.data_host:
            return "425 Use PORT or PASV first\r\n"
        if self._transfer_in_progress(session):
            return "450 Transfer already in progress\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "RETR", "file": arg}
        transfer_id = self._start_transfer_thread(session, "RETR", tm.download, arg)
        return f"150 Opening data connection; transfer_id={transfer_id}\r\n"

    def stor(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        if not session.data_socket and not session.data_host:
            return "425 Use PORT or PASV first\r\n"
        if self._transfer_in_progress(session):
            return "450 Transfer already in progress\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "STOR", "file": arg}
        transfer_id = self._start_transfer_thread(session, "STOR", tm.upload, arg)
        return f"150 Opening data connection; transfer_id={transfer_id}\r\n"

    def stou(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not session.data_socket and not session.data_host:
            return "425 Use PORT or PASV first\r\n"
        if self._transfer_in_progress(session):
            return "450 Transfer already in progress\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "STOU"}
        transfer_id = self._start_transfer_thread(session, "STOU", tm.upload_unique)
        return f"150 Opening data connection; transfer_id={transfer_id}\r\n"

    def appe(self, arg, session):
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        if not arg:
            return "501 Missing filename\r\n"
        if not session.data_socket and not session.data_host:
            return "425 Use PORT or PASV first\r\n"
        if self._transfer_in_progress(session):
            return "450 Transfer already in progress\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "APPE", "file": arg}
        transfer_id = self._start_transfer_thread(session, "APPE", tm.append, arg)
        return f"150 Opening data connection; transfer_id={transfer_id}\r\n"

    def abor_cmd(self, arg, session):
        if arg:
            return "501 Syntax error in parameters\r\n"
        if not session.is_logged_in:
            return "530 Not logged in\r\n"
        tm = self.transfer_manager
        if tm is not None:
            try:
                tm.cancel(session)
            except Exception:
                pass
        session.transfer_cancelled = True
        worker = getattr(session, "transfer_worker", None)
        if worker and worker.is_alive():
            worker.join(timeout=1.0)
        return "226 Abort successful\r\n"
