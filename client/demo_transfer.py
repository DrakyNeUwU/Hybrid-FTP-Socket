"""Run one upload/download Hybrid FTP demo against a running local server."""

from __future__ import annotations

import argparse
import sys

from client.cli_display import render_progress_bar
from client.ftp_client import FTPClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid FTP UDP/RDT demo")
    parser.add_argument("local_file", help="local file to upload")
    parser.add_argument("--remote", default=None, help="remote filename")
    parser.add_argument("--mode", choices=("PASV", "ACTIVE"), default="PASV")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2121)
    args = parser.parse_args()

    remote = args.remote or args.local_file.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    def show_progress(direction: str, filename: str, transferred: int, total: int | None) -> None:
        total_bytes = total if total is not None else transferred
        print(render_progress_bar(f"{direction}: {filename}", transferred, total_bytes))

    client = FTPClient(args.host, args.port, progress_callback=show_progress)
    try:
        print(client.connect().strip())
        client.login()
        if not client.upload_file(args.local_file, remote, mode=args.mode):
            print("Upload failed")
            return 1
        if not client.download_file(remote, mode=args.mode):
            print("Download failed")
            return 1
        print(f"Success: {args.mode} upload + download for {remote}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
