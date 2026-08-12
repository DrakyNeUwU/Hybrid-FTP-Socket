"""Interactive terminal client for Hybrid FTP control and RDT transfers."""

from __future__ import annotations

import argparse
import os
import shlex

from client.ftp_client import FTPClient


def _upload_arguments(parts: list[str]) -> tuple[str, str]:
    """Return local and remote names for STOR/APPE terminal syntax."""
    if len(parts) not in (2, 3):
        raise ValueError(f"Usage: {parts[0].upper()} <local-file> [remote-file]")
    local_file = parts[1]
    if not os.path.isfile(local_file):
        raise ValueError(f"Local file not found: {local_file}")
    return local_file, parts[2] if len(parts) == 3 else os.path.basename(local_file)


def run_command(client: FTPClient, line: str, data_mode: str) -> tuple[str, bool]:
    """Run one terminal command and return its printable result and quit state."""
    parts = shlex.split(line)
    if not parts:
        return "", False
    command = parts[0].upper()

    if command in {"STOR", "APPE"}:
        local_file, remote_file = _upload_arguments(parts)
        ok = client.upload_file(
            local_file, remote_file, cmd=command, mode=data_mode, reply_callback=print
        )
        return ("226 Transfer complete" if ok else "Transfer failed"), False
    if command == "STOU":
        if len(parts) != 2 or not os.path.isfile(parts[1]):
            raise ValueError("Usage: STOU <local-file>")
        ok = client.upload_unique_file(parts[1], mode=data_mode, reply_callback=print)
        return ("226 Transfer complete" if ok else "Transfer failed"), False
    if command == "RETR":
        if len(parts) != 2:
            raise ValueError("Usage: RETR <remote-file>")
        ok = client.download_file(parts[1], mode=data_mode, reply_callback=print)
        return ("226 Transfer complete" if ok else "Transfer failed"), False

    return client.command(line).strip(), command == "QUIT"


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive Hybrid FTP terminal client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2121)
    parser.add_argument("--data-mode", choices=("PASV", "ACTIVE"), default="PASV")
    args = parser.parse_args()

    client = FTPClient(args.host, args.port)
    quit_sent = False
    try:
        print(client.connect().strip())
        while True:
            try:
                line = input("ftp> ").strip()
                result, quit_sent = run_command(client, line, args.data_mode)
                if result:
                    print(result)
                if quit_sent:
                    return 0
            except (OSError, RuntimeError, ValueError) as exc:
                print(f"Error: {exc}")
            except EOFError:
                print()
                return 0
    except KeyboardInterrupt:
        print()
        return 130
    finally:
        if not quit_sent:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
