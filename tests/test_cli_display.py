"""
test_cli_display.py — Unit test cho module client/cli_display.py

=== WHAT THIS TEST COVERS ===
  1. format_size converts byte counts accurately to KB, MB, and GB.
  2. render_header displays IP, port, status, user, and CWD.
  3. render_progress_bar calculates the percentage and proportional bar.
  4. render_directory_list formats a standard file/directory table.

=== RUN ===
  py -m pytest tests/test_cli_display.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.cli_display import (
    format_size,
    render_header,
    render_progress_bar,
    render_directory_list,
)
from client.demo_transfer import _console_safe


class TestCLIDisplay:
    """Unit tests for the CLI display."""

    def test_format_size_bytes(self):
        """Check formatting at several sizes."""
        assert format_size(0) == "0 B"
        assert format_size(500) == "500 B"
        assert format_size(1024) == "1.00 KB"
        assert format_size(1572864) == "1.50 MB"
        assert format_size(1073741824) == "1.00 GB"

    def test_render_header_connected(self):
        """Check the connected header."""
        header = render_header("127.0.0.1", 2121, True, "/home/ftp", "khanh")
        assert "127.0.0.1:2121" in header
        assert "CONNECTED" in header
        assert "/home/ftp" in header
        assert "khanh" in header

    def test_render_header_disconnected(self):
        """Check the disconnected header."""
        header = render_header("192.168.1.1", 21, False)
        assert "DISCONNECTED" in header

    def test_render_progress_bar_calculation(self):
        """Check a 50% progress bar."""
        bar = render_progress_bar("test.zip", 50, 100, 1024.0, width=10)
        assert "50.0%" in bar
        assert "File: test.zip" in bar
        assert "█████░░░░░" in bar  # 50% of width 10 fills five characters
        assert "50 B / 100 B" in bar

    def test_render_directory_list_empty(self):
        """Check an empty directory listing."""
        output = render_directory_list([])
        assert "(Directory is empty)" in output

    def test_render_directory_list_formatting(self):
        """Check file/directory table formatting."""
        entries = [
            {"name": "docs", "size": 0, "type": "dir", "permissions": "rwxr-xr-x", "modified": "20260724120000"},
            {"name": "image.png", "size": 1048576, "type": "file", "permissions": "rw-r--r--", "modified": "20260724120500"},
        ]
        output = render_directory_list(entries)
        
        assert "<DIR>" in output
        assert "<FILE>" in output
        assert "docs" in output
        assert "image.png" in output
        assert "1.00 MB" in output

    def test_demo_console_falls_back_when_code_page_cannot_render_progress(self):
        assert _console_safe("[██░░]", "cp1252") == "[????]"
        assert _console_safe("plain text", "cp1252") == "plain text"
