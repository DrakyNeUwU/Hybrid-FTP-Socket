"""Run one upload/download Hybrid FTP demo against a running local server."""

from __future__ import annotations

import argparse
import sys

from client.cli_display import render_progress_bar
from client.ftp_client import FTPClient


def _console_safe(value: str, encoding: str | None = None) -> str:
    """Return text printable by the active terminal without aborting a transfer."""
    target_encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        value.encode(target_encoding)
    except UnicodeEncodeError:
        return value.encode(target_encoding, errors="replace").decode(target_encoding)
    return value


def _print_console(value: str) -> None:
    print(_console_safe(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid FTP UDP/RDT demo")
    parser.add_argument("local_file", help="local file to upload")
    parser.add_argument("--remote", default=None, help="remote filename")
    parser.add_argument("--mode", choices=("PASV", "ACTIVE"), default="PASV")
    parser.add_argument(
        "--transfer-mode",
        choices=("S", "B", "C"),
        default="S",
        help="FTP transmission mode: S=Stream, B=Block, C=Compressed",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2121)
    parser.add_argument("--username", help="server account username")
    parser.add_argument("--password", help="server account password")
    args = parser.parse_args()

    remote = args.remote or args.local_file.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    def show_progress(direction: str, filename: str, transferred: int, total: int | None) -> None:
        total_bytes = total if total is not None else transferred
        _print_console(render_progress_bar(f"{direction}: {filename}", transferred, total_bytes))

    client = FTPClient(args.host, args.port, progress_callback=show_progress,
                       transfer_mode=args.transfer_mode)
    try:
        _print_console(client.connect().strip())
        username = args.username or input("Username: ").strip()
        password = args.password if args.password is not None else input("Password: ")
        client.login(username, password)
        _print_console(client.set_mode(args.transfer_mode).strip())
        if not client.upload_file(args.local_file, remote, mode=args.mode):
            _print_console("Upload failed")
            return 1
        if not client.download_file(remote, mode=args.mode):
            _print_console("Download failed")
            return 1
        _print_console(f"Success: {args.mode} {args.transfer_mode} upload + download for {remote}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
