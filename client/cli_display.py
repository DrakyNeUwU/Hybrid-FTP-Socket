"""
cli_display.py — CLI formatting and display module for the FTP client.

Provides terminal presentation helpers for file sizes, connection status,
transfer progress, and directory listings. client/client.py calls these
helpers while the user interacts with the CLI.
"""

import sys
import math


def format_size(bytes_count: int) -> str:
    """
    Convert a raw byte count into a human-readable size.

    Examples:
      1024       -> "1.00 KB"
      1572864    -> "1.50 MB"
      1073741824 -> "1.00 GB"
    """
    if bytes_count <= 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    digit_group = int(math.floor(math.log(bytes_count, 1024)))
    digit_group = min(digit_group, len(units) - 1)
    
    val = bytes_count / (1024 ** digit_group)
    
    if digit_group == 0:
        return f"{int(val)} B"
    return f"{val:.2f} {units[digit_group]}"


def render_header(server_ip: str, port: int, connected: bool, cwd: str = "/", user: str = None) -> str:
    """
    Format the connection-status header.
    """
    status_str = "● CONNECTED" if connected else "○ DISCONNECTED"
    user_str = user if user else "Anonymous / Not logged in"
    
    lines = [
        "┌────────────────────────────────────────────────────────┐",
        "│  HYBRID FTP CLIENT                               v1.0  │",
        "├────────────────────────────────────────────────────────┤",
        f"│ Server: {server_ip}:{port:<5}  | Status: {status_str:<18} │",
        f"│ User  : {user_str:<46} │",
        f"│ CWD   : {cwd:<46} │",
        "└────────────────────────────────────────────────────────┘"
    ]
    return "\n".join(lines)


def render_progress_bar(filename: str, transferred: int, total: int, speed_bytes_sec: float = 0.0, width: int = 30) -> str:
    """
    Create a file-transfer progress-bar string.

    Example output:
      Downloading: sample.zip
      [████████████████████████░░░░░░░░░░] 60.0% (6.00 MB / 10.00 MB) - 1.20 MB/s
    """
    if total <= 0:
        percentage = 100.0
        filled_len = width
    else:
        percentage = min(100.0, (transferred / total) * 100.0)
        filled_len = int(round(width * transferred / float(total)))
        filled_len = min(width, filled_len)

    bar = '█' * filled_len + '░' * (width - filled_len)
    
    transferred_fmt = format_size(transferred)
    total_fmt = format_size(total) if total > 0 else "Unknown"
    speed_fmt = f"{format_size(int(speed_bytes_sec))}/s" if speed_bytes_sec > 0 else "-- B/s"

    output = (
        f"File: {filename}\n"
        f"[{bar}] {percentage:5.1f}% ({transferred_fmt} / {total_fmt}) | Speed: {speed_fmt}"
    )
    return output


def render_directory_list(entries: list) -> str:
    """
    Format entries from dir_manager.list_directory as a readable table.

    Input entry dict format:
      {"name": str, "size": int, "type": "file"/"dir", "permissions": str, "modified": str}
    """
    if not entries:
        return "(Directory is empty)"

    header = f"{'TYPE':<6} {'PERMISSIONS':<11} {'SIZE':<10} {'MODIFIED':<16} {'NAME'}"
    divider = "-" * len(header)
    lines = [header, divider]

    for entry in entries:
        type_str = "<DIR>" if entry["type"] == "dir" else "<FILE>"
        size_str = "-" if entry["type"] == "dir" else format_size(entry["size"])
        perm_str = entry.get("permissions", "---------")
        mod_str = entry.get("modified", "----------------")
        
        lines.append(f"{type_str:<6} {perm_str:<11} {size_str:<10} {mod_str:<16} {entry['name']}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick visual-display test.
    print(render_header("127.0.0.1", 2121, True, "/docs/reports", "admin"))
    print()
    print(render_progress_bar("report_2026.pdf", 6291456, 10485760, 1258291.2))
    print()
    
    dummy_entries = [
        {"name": "docs", "size": 0, "type": "dir", "permissions": "rwxr-xr-x", "modified": "20260724120000"},
        {"name": "photo.png", "size": 2500000, "type": "file", "permissions": "rw-r--r--", "modified": "20260724113000"},
    ]
    print(render_directory_list(dummy_entries))
