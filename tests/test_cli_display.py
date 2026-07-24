"""
test_cli_display.py — Unit test cho module client/cli_display.py

=== TEST NÀY KIỂM TRA GÌ? ===
  1. Hàm format_size đổi dung lượng byte thành KB, MB, GB chính xác.
  2. Hàm render_header hiển thị đủ thông tin IP, port, status, user, CWD.
  3. Hàm render_progress_bar tính % tiến trình và hiển thị thanh bar đúng tỷ lệ.
  4. Hàm render_directory_list định dạng bảng danh sách file/thư mục chuẩn.

=== CÁCH CHẠY ===
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


class TestCLIDisplay:
    """Tập hợp unit test cho giao diện CLI."""

    def test_format_size_bytes(self):
        """Kiểm tra format các mức dung lượng khác nhau."""
        assert format_size(0) == "0 B"
        assert format_size(500) == "500 B"
        assert format_size(1024) == "1.00 KB"
        assert format_size(1572864) == "1.50 MB"
        assert format_size(1073741824) == "1.00 GB"

    def test_render_header_connected(self):
        """Kiểm tra render header ở trạng thái đã kết nối."""
        header = render_header("127.0.0.1", 2121, True, "/home/ftp", "khanh")
        assert "127.0.0.1:2121" in header
        assert "CONNECTED" in header
        assert "/home/ftp" in header
        assert "khanh" in header

    def test_render_header_disconnected(self):
        """Kiểm tra render header ở trạng thái ngắt kết nối."""
        header = render_header("192.168.1.1", 21, False)
        assert "DISCONNECTED" in header

    def test_render_progress_bar_calculation(self):
        """Kiểm tra hiển thị thanh tiến trình 50%."""
        bar = render_progress_bar("test.zip", 50, 100, 1024.0, width=10)
        assert "50.0%" in bar
        assert "File: test.zip" in bar
        assert "█████░░░░░" in bar  # 50% của width 10 là 5 ký tự filled
        assert "50 B / 100 B" in bar

    def test_render_directory_list_empty(self):
        """Kiểm tra danh sách thư mục rỗng."""
        output = render_directory_list([])
        assert "(Directory is empty)" in output

    def test_render_directory_list_formatting(self):
        """Kiểm tra định dạng bảng danh sách file/dir."""
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
