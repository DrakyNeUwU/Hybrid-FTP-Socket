"""Thread-safe, password-safe logging shared by server components."""

from __future__ import annotations

import threading
import time


_LOG_LOCK = threading.Lock()


def safe_log(message: str) -> None:
    """Print one timestamped server event without interleaving threads."""

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with _LOG_LOCK:
        print(f"[{timestamp}] {message}", flush=True)


def redact_command(command: str) -> str:
    """Hide PASS arguments before a command is written to a log."""

    verb, separator, _ = command.partition(" ")
    return f"{verb} ********" if separator and verb.upper() == "PASS" else command
