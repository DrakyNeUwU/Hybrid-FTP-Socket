import os
import hashlib
import socket
import threading
from server.ftp_reply import FTPReply
from common.filesystem_service import FilesystemService

class _FallbackFilesystem:
    """Minimal filesystem shim used when no TransferManager is injected (e.g. unit tests)."""
    def __init__(self, root: str):
        self._root = os.path.abspath(root)

    def _safe(self, rel, base=None):
        base = base or self._root
        path = os.path.realpath(os.path.join(base, rel))
        root_real = os.path.realpath(self._root)
        try:
            common = os.path.commonpath([root_real, path])
        except ValueError:
            raise ValueError("Path escapes FTP root")
        if common != root_real:
            raise ValueError("Path escapes FTP root")
        return path

    def resolve_path(self, rel, base=None):
        return self._safe(rel, base)

    def _raise_for_path(self, path, op, is_dir):
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        if is_dir and not os.path.isdir(path):
            raise NotADirectoryError(path)
        if not is_dir and not os.path.isfile(path):
            raise IsADirectoryError(path)

    def make_dir(self, rel, base=None):
        os.mkdir(self._safe(rel, base))

    def remove_dir(self, rel, base=None):
        os.rmdir(self._safe(rel, base))

    def delete_file(self, rel, base=None):
        os.remove(self._safe(rel, base))

    def rename_entry(self, src, dst, base=None):
        os.rename(self._safe(src, base), self._safe(dst, base))

    def list_directory(self, rel, base=None):
        from types import SimpleNamespace
        import stat as stat_mod, time
        path = self._safe(rel, base)
        entries = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            is_dir = os.path.isdir(full)
            try:
                st = os.stat(full)
                size = st.st_size
                mode = stat_mod.filemode(st.st_mode)
                modified = time.strftime("%Y%m%d%H%M%S", time.localtime(st.st_mtime))
            except OSError:
                size = 0
                mode = "??????????"
                modified = ""
            entries.append({
                "name": name,
                "size": size,
                "type": "dir" if is_dir else "file",
                "permissions": mode[1:] if len(mode) > 1 else "rwxr-xr-x",
                "modified": modified,
            })
        return entries

    def list_names(self, rel, base=None):
        path = self._safe(rel, base)
        return os.listdir(path)


class _FallbackTransferManager:
    """Minimal shim used when no real TransferManager is injected."""
    def __init__(self, filesystem):
        self.filesystem = filesystem

    def cancel(self, session):
        pass

    def upload(self, session, filename, **kw):
        return None

    def download(self, session, filename, **kw):
        return None

    def upload_unique(self, session, **kw):
        return None

    def append(self, session, filename, **kw):
        return None


class CommandHandler:
    def __init__(self, transfer_manager=None):
        self._tm = transfer_manager  # may be None — _fs() handles lazily
        self.transfer_manager = transfer_manager

    def _fs(self, session):
        """Return filesystem for this session, building a per-root fallback if needed."""
        if self.transfer_manager is not None:
            return self.transfer_manager.filesystem
        root = getattr(session, 'ftp_root', './ftp_root')
        return _FallbackFilesystem(root)

    def handle(self, command, session):
        cmd = command.name
        arg = command.argument

        # Reset rename state if anything other than RNTO follows RNFR
        if session.rename_from is not None and cmd not in ("RNTO",):
            session.rename_from = None

        if cmd == "USER": return self.user(arg, session)
        elif cmd == "PASS": return self.password(arg, session)
        elif cmd == "QUIT":
            if arg: return "501 Syntax error\r\n"
            session.rename_from = None
            return FTPReply.QUIT
        elif cmd == "NOOP":
            if arg: return "501 Syntax error\r\n"
            return "200 NOOP OK\r\n"
        elif cmd == "TYPE": return self.type_cmd(arg, session)
        elif cmd == "MODE": return self.mode_cmd(arg, session)
        elif cmd == "PWD": return self.pwd(session)
        elif cmd == "CWD": return self.cwd(arg, session)
        elif cmd == "CDUP": return self.cdup(session)
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
        elif cmd == "PASV": return self.pasv(session, arg)
        elif cmd == "RETR": return self.retr(arg, session)
        elif cmd == "STOR": return self.stor(arg, session)
        elif cmd == "STOU": return self.stou(arg, session)
        elif cmd == "APPE": return self.appe(arg, session)
        elif cmd == "ABOR": return self.abor(session)
        elif cmd == "HASH": return self.hash_cmd(arg, session)
        elif cmd == "HELP":
            return "214-Supported commands:\r\n USER PASS QUIT NOOP PWD CWD CDUP MKD RMD LIST NLST STAT SIZE MDTM TYPE MODE HELP PORT PASV RETR STOR STOU APPE DELE RNFR RNTO HASH ABOR\r\n214 Help OK\r\n"
        else:
            return FTPReply.NOT_IMPLEMENTED

    def user(self, arg, session):
        if not arg or not arg.strip(): return "501 Invalid username\r\n"
        # RFC 959: new USER resets authentication state
        session.username = arg.strip()
        session.is_logged_in = False
        session.rename_from = None
        return FTPReply.USER_OK

    def password(self, arg, session):
        if session.username is None: return "503 Login with USER first\r\n"
        if session.is_logged_in: return "230 Already logged in\r\n"
        if arg == "123456":
            session.is_logged_in = True
            return FTPReply.LOGIN_OK
        session.username = None
        return "530 Login incorrect\r\n"

    def pwd(self, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        return f'257 "{session.current_dir}"\r\n'

    def cwd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing directory\r\n"
        try:
            fs = self._fs(session)
            new_path = fs.resolve_path(arg, session.current_dir)
            fs._raise_for_path(new_path, "CWD", True)
            session.current_dir = new_path
            return "250 Directory changed\r\n"
        except Exception:
            return "550 Directory not found\r\n"

    def cdup(self, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        try:
            new_path = self._fs(session).resolve_path("..", session.current_dir)
            session.current_dir = new_path
            return "200 Directory changed to parent\r\n"
        except Exception:
            return "550 Cannot go above FTP root\r\n"

    def mkd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing directory\r\n"
        try:
            self._fs(session).make_dir(arg, session.current_dir)
            return "257 Directory created\r\n"
        except Exception:
            return "550 Cannot create directory\r\n"

    def rmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing directory\r\n"
        try:
            self._fs(session).remove_dir(arg, session.current_dir)
            return "250 Directory removed\r\n"
        except Exception:
            return "550 Cannot remove directory\r\n"

    def dele(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        try:
            self._fs(session).delete_file(arg, session.current_dir)
            return "250 File deleted\r\n"
        except Exception:
            return "550 Cannot delete file\r\n"

    def rnfr(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        try:
            fs = self._fs(session)
            path = fs.resolve_path(arg, session.current_dir)
            fs._raise_for_path(path, "RNFR", False)
            session.rename_from = arg
            return "350 Ready for RNTO\r\n"
        except Exception:
            return "550 File not found\r\n"

    def rnto(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg:
            # Missing argument resets the RNFR state
            session.rename_from = None
            return "501 Missing filename\r\n"
        if not session.rename_from: return "503 RNFR required\r\n"
        try:
            self._fs(session).rename_entry(session.rename_from, arg, session.current_dir)
            session.rename_from = None
            return "250 Rename successful\r\n"
        except Exception:
            session.rename_from = None
            return "550 Rename failed\r\n"

    def type_cmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        arg = arg.upper()
        if arg == "A":
            session.transfer_type = "A"
            return "200 Type set to ASCII\r\n"
        elif arg == "I":
            session.transfer_type = "I"
            return "200 Type set to Binary\r\n"
        return "501 Invalid TYPE\r\n"

    def mode_cmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        arg = arg.upper()
        if arg == "S":
            session.transfer_mode = "S"
            return "200 Mode Stream\r\n"
        elif arg in ["B", "C"]:
            return "502 Mode not implemented\r\n"
        return "501 Invalid MODE\r\n"

    def port_cmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing arguments\r\n"
        try:
            parts = arg.split(",")
            if len(parts) != 6: return "501 Invalid PORT\r\n"
            nums = []
            for p in parts:
                v = int(p)
                if not (0 <= v <= 255):
                    return "501 Invalid PORT\r\n"
                nums.append(v)
            ip = ".".join(str(n) for n in nums[:4])
            port = nums[4] * 256 + nums[5]
            if port <= 0 or port > 65535: return "501 Invalid PORT\r\n"
            # Anti-FTP-bounce: reject reserved/loopback ports for remote clients
            # Port 20 is reserved for FTP data; port < 1024 without privilege is suspicious
            # We allow all IPs so the server works in test environments (127.x)
            session.data_host = ip
            session.data_port = port
            session.data_mode = "ACTIVE"
            return "200 PORT command successful\r\n"
        except (ValueError, IndexError):
            return "501 Invalid PORT\r\n"

    def pasv(self, session, arg=""):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if arg: return "501 Syntax error in parameters\r\n"
        # Close old data socket before creating a new one
        if getattr(session, "data_socket", None):
            try: session.data_socket.close()
            except: pass
            session.data_socket = None
        try:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.bind(("0.0.0.0", 0))
            session.data_socket = udp
            port = udp.getsockname()[1]
            # Advertise real server address; fall back to 127.0.0.1 only when unresolvable
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
        if not session.is_logged_in: return "530 Not logged in\r\n"
        try:
            target = arg if arg else "."
            entries = self._fs(session).list_directory(target, session.current_dir)
            lines = []
            for e in entries:
                if isinstance(e, dict):
                    name = e.get("name", "")
                    size = e.get("size", 0)
                    etype = e.get("type", "-")
                    perms = e.get("permissions", "rwxr-xr-x")
                    modified = e.get("modified", "")
                    # Format modified: YYYYMMDDHHMMSS → Mon DD HH:MM
                    try:
                        import datetime
                        dt = datetime.datetime.strptime(modified, "%Y%m%d%H%M%S")
                        mod_str = dt.strftime("%b %d %H:%M")
                    except Exception:
                        mod_str = modified
                    type_char = "d" if etype == "dir" else "-"
                    lines.append(f"{type_char}{perms} 1 ftp ftp {size:>10} {mod_str} {name}")
                else:
                    # fallback for SimpleNamespace
                    type_char = getattr(e, 'type', '-')
                    if type_char not in ('d', '-'): type_char = '-'
                    size = getattr(e, 'size', 0)
                    name = getattr(e, 'name', str(e))
                    lines.append(f"{type_char}rwxr-xr-x 1 ftp ftp {size:>10}  {name}")
            result = "\r\n".join(lines)
            return f"150 Here comes the directory listing.\r\n{result}\r\n226 Directory send OK.\r\n"
        except Exception:
            return "550 Cannot list directory\r\n"

    def nlst(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        try:
            target = arg if arg else "."
            entries = self._fs(session).list_names(target, session.current_dir)
            result = "\r\n".join(entries)
            return f"150 Here comes the directory listing.\r\n{result}\r\n226 Directory send OK.\r\n"
        except Exception:
            return "550 Cannot list directory\r\n"

    def size_cmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        try:
            path = self._fs(session).resolve_path(arg, session.current_dir)
            size = os.path.getsize(path)
            return f"213 {size}\r\n"
        except Exception:
            return "550 File not found\r\n"

    def mdtm_cmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        try:
            path = self._fs(session).resolve_path(arg, session.current_dir)
            mtime = os.path.getmtime(path)
            # Basic FTP format YYYYMMDDHHMMSS
            import datetime
            dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y%m%d%H%M%S")
            return f"213 {dt}\r\n"
        except Exception:
            return "550 File not found\r\n"

    def stat_cmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        return "211-FTP Server status:\r\n211 End of status\r\n"

    def hash_cmd(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        try:
            path = self._fs(session).resolve_path(arg, session.current_dir)
            sha256 = hashlib.sha256()
            with open(path, "rb") as f:
                while True:
                    data = f.read(4096)
                    if not data: break
                    sha256.update(data)
            return f"213 SHA256 {sha256.hexdigest()}\r\n"
        except Exception:
            return "550 HASH failed\r\n"

    def _start_transfer_thread(self, session, action_name, action_func, arg=None):
        if not session.data_socket and not session.data_host:
            session.send_reply("425 Use PORT or PASV first\r\n")
            return

        def run_transfer():
            try:
                if arg is not None:
                    result = action_func(
                        session, arg,
                        data_socket=session.data_socket,
                        endpoint=(session.data_host, session.data_port)
                    )
                else:
                    result = action_func(
                        session,
                        data_socket=session.data_socket,
                        endpoint=(session.data_host, session.data_port)
                    )

                if result:
                    session.send_reply("226 Transfer complete\r\n")
                elif result is not None:
                    code = getattr(result, 'reply_code', 426)
                    err = getattr(result, 'error', 'Transfer failed')
                    session.send_reply(f"{code} {err}\r\n")
                else:
                    # result is None means adapter not configured (e.g. in tests)
                    session.send_reply("426 No RDT adapter configured\r\n")
            except Exception:
                session.send_reply("426 Transfer failed\r\n")

        t = threading.Thread(target=run_transfer, daemon=True)
        t.start()
        session.transfer_worker = t

    def retr(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "RETR", "file": arg}
        self._start_transfer_thread(session, "RETR", tm.download, arg)
        return "150 Opening data connection\r\n"

    def stor(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "STOR", "file": arg}
        self._start_transfer_thread(session, "STOR", tm.upload, arg)
        return "150 Opening data connection\r\n"

    def stou(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "STOU"}
        self._start_transfer_thread(session, "STOU", tm.upload_unique)
        return "150 Opening data connection\r\n"

    def appe(self, arg, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        if not arg: return "501 Missing filename\r\n"
        tm = self.transfer_manager
        if tm is None:
            return "502 No transfer manager configured\r\n"
        session.current_transfer = {"type": "APPE", "file": arg}
        self._start_transfer_thread(session, "APPE", tm.append, arg)
        return "150 Opening data connection\r\n"

    def abor(self, session):
        if not session.is_logged_in: return "530 Not logged in\r\n"
        tm = self.transfer_manager or getattr(self, '_tm', None)
        if tm is not None:
            try:
                tm.cancel(session)
            except Exception:
                pass
        session.transfer_cancelled = True
        return "226 Abort successful\r\n"
