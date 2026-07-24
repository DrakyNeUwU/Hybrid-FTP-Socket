"""
test_file_handler.py — Test cho module common/file_handler.py

=== TEST NÀY KIỂM TRA GÌ? ===
  1. Đọc/ghi file text và binary → nội dung giống nhau trước/sau
  2. Chia file thành chunks rồi ráp lại → byte-by-byte giống file gốc
  3. Hash nhất quán (cùng file → cùng hash, khác file → khác hash)
  4. Append ghi nối tiếp đúng
  5. Edge cases: file rỗng, file 1 byte, file kích thước = chunk_size

=== CÁCH CHẠY ===
  cd <project-root>
  python -m pytest tests/test_file_handler.py -v
"""

import os
import sys
import tempfile
import shutil

import pytest

# Thêm thư mục gốc dự án vào sys.path để import được module common
# __file__ = tests/test_file_handler.py
# parent of parent = thư mục gốc dự án
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.file_handler import (
    read_file,
    write_file,
    read_file_chunks,
    write_file_from_chunks,
    append_to_file,
    compute_hash,
    get_file_size,
    file_exists,
    DEFAULT_CHUNK_SIZE,
)


# ============================================================
# FIXTURES — Chuẩn bị môi trường test
# ============================================================

@pytest.fixture
def temp_dir():
    """
    Tạo 1 thư mục tạm trước mỗi test, tự xoá sau khi test xong.

    Tại sao dùng thư mục tạm?
      - Mỗi test cần tạo file để test đọc/ghi
      - Nếu dùng thư mục cố định, test chạy đồng thời sẽ xung đột
      - tempfile.mkdtemp() tạo thư mục unique (ví dụ: /tmp/tmp_a3f2e8/)
      - yield: chạy phần trước yield TRƯỚC test, phần sau yield SAU test
    """
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)  # Xoá sạch thư mục tạm sau khi test xong


@pytest.fixture
def sample_text_data():
    """Dữ liệu text mẫu (ASCII) — dùng cho test Basic tier."""
    return b"Hello, this is a sample FTP file.\nLine 2.\nLine 3 end."


@pytest.fixture
def sample_binary_data():
    """
    Dữ liệu binary mẫu — mô phỏng file ảnh/archive.

    Tại sao tạo dữ liệu với mọi giá trị byte (0x00 → 0xFF)?
      - File binary thật (JPEG, ZIP...) chứa mọi giá trị byte
      - Byte 0x00 (null) hay bị "nuốt" nếu đọc/ghi sai mode (text thay vì binary)
      - Byte 0x1A (Ctrl+Z) khiến Windows text mode nghĩ là EOF
      - Byte 0x0D 0x0A (\\r\\n) bị text mode tự chuyển đổi
      - Nếu test pass với dữ liệu này → đảm bảo hoạt động với mọi file binary thật
    """
    # Tạo 5 vòng 256 bytes (0x00-0xFF) = 1280 bytes > 1 chunk (1024)
    # → sẽ test được cả trường hợp file lớn hơn 1 chunk
    return bytes(range(256)) * 5


@pytest.fixture
def large_binary_data():
    """Dữ liệu binary lớn — test nhiều chunks."""
    # 10240 bytes = 10 chunks đúng (nếu chunk_size = 1024)
    return os.urandom(10240)


# ============================================================
# TEST ĐỌC/GHI CƠ BẢN
# ============================================================

class TestReadWriteFile:
    """Test nhóm hàm read_file / write_file — đọc/ghi cơ bản."""

    def test_write_then_read_text(self, temp_dir, sample_text_data):
        """
        Ghi dữ liệu text → đọc lại → phải giống byte-by-byte.
        Đây là kịch bản cơ bản nhất: FTP Basic tier (ASCII file).
        """
        path = os.path.join(temp_dir, "test.txt")
        bytes_written = write_file(path, sample_text_data)
        result = read_file(path)

        assert result == sample_text_data, "Nội dung đọc lại phải giống nội dung ghi"
        assert bytes_written == len(sample_text_data), "Số bytes ghi phải = len(data)"

    def test_write_then_read_binary(self, temp_dir, sample_binary_data):
        """
        Ghi dữ liệu binary (chứa 0x00, 0xFF...) → đọc lại → phải giống.
        Đây là test QUAN TRỌNG NHẤT — nếu fail nghĩa là mode binary sai.
        """
        path = os.path.join(temp_dir, "test.bin")
        write_file(path, sample_binary_data)
        result = read_file(path)

        assert result == sample_binary_data, "Binary data phải giữ nguyên qua write/read"

    def test_write_creates_parent_directories(self, temp_dir):
        """
        Ghi file vào thư mục con chưa tồn tại → tự tạo thư mục.
        Ví dụ: client upload file vào /ftp/docs/2026/ nhưng thư mục 2026/ chưa có.
        """
        path = os.path.join(temp_dir, "sub", "deep", "file.txt")
        write_file(path, b"nested file content")

        assert os.path.isfile(path), "File phải được tạo kể cả khi thư mục cha chưa có"
        assert read_file(path) == b"nested file content"

    def test_write_overwrites_existing(self, temp_dir):
        """
        Ghi file đã tồn tại → nội dung mới thay thế nội dung cũ.
        Đây là hành vi của lệnh STOR (store) — ghi đè.
        """
        path = os.path.join(temp_dir, "overwrite.txt")
        write_file(path, b"original content")
        write_file(path, b"new content")

        assert read_file(path) == b"new content", "write_file phải ghi đè hoàn toàn"

    def test_read_nonexistent_file_raises(self, temp_dir):
        """Đọc file không tồn tại → FileNotFoundError (reply code 550)."""
        with pytest.raises(FileNotFoundError):
            read_file(os.path.join(temp_dir, "does_not_exist.txt"))


# ============================================================
# TEST CHUNK — CHIA NHỎ & RÁP LẠI
# ============================================================

class TestChunks:
    """
    Test read_file_chunks / write_file_from_chunks.
    Đây là phần cốt lõi — kết nối file_handler với Role B (UDP sender/receiver).
    """

    def test_chunks_reassemble_text(self, temp_dir, sample_text_data):
        """
        Chia file text thành chunks → ráp lại → giống file gốc.
        Kiểm tra: nội dung không bị mất hay thay đổi qua quá trình split/merge.
        """
        # Ghi file gốc
        src = os.path.join(temp_dir, "source.txt")
        write_file(src, sample_text_data)

        # Đọc theo chunks
        chunks = list(read_file_chunks(src))

        # Ráp lại
        dst = os.path.join(temp_dir, "reassembled.txt")
        write_file_from_chunks(dst, chunks)

        assert read_file(dst) == sample_text_data, "Ráp chunks lại phải giống file gốc"

    def test_chunks_reassemble_binary(self, temp_dir, sample_binary_data):
        """
        Chia file binary thành chunks → ráp lại → PHẢI giống byte-by-byte.
        Test quan trọng nhất cho Advanced tier (binary file handling).
        """
        src = os.path.join(temp_dir, "photo.bin")
        write_file(src, sample_binary_data)

        chunks = list(read_file_chunks(src))
        dst = os.path.join(temp_dir, "photo_copy.bin")
        write_file_from_chunks(dst, chunks)

        original = read_file(src)
        reassembled = read_file(dst)
        assert original == reassembled, "Binary file phải giữ nguyên qua chunk split/merge"

    def test_chunk_sizes_correct(self, temp_dir, sample_binary_data):
        """
        Kiểm tra kích thước chunk: tất cả chunk ngoại trừ chunk cuối
        phải có đúng DEFAULT_CHUNK_SIZE bytes. Chunk cuối có thể nhỏ hơn.
        """
        path = os.path.join(temp_dir, "sized.bin")
        write_file(path, sample_binary_data)

        chunks = list(read_file_chunks(path))

        # Tất cả chunk trừ cuối phải = DEFAULT_CHUNK_SIZE
        for chunk in chunks[:-1]:
            assert len(chunk) == DEFAULT_CHUNK_SIZE, (
                f"Chunk giữa phải = {DEFAULT_CHUNK_SIZE} bytes, got {len(chunk)}"
            )

        # Chunk cuối <= DEFAULT_CHUNK_SIZE
        assert 0 < len(chunks[-1]) <= DEFAULT_CHUNK_SIZE

        # Tổng bytes tất cả chunks = kích thước file gốc
        total = sum(len(c) for c in chunks)
        assert total == len(sample_binary_data), "Tổng bytes chunks = file gốc"

    def test_custom_chunk_size(self, temp_dir, sample_binary_data):
        """Chunk size tuỳ chỉnh (ví dụ 512) hoạt động đúng."""
        path = os.path.join(temp_dir, "custom.bin")
        write_file(path, sample_binary_data)

        chunks = list(read_file_chunks(path, chunk_size=512))
        reassembled = b"".join(chunks)

        assert reassembled == sample_binary_data

    def test_large_file_chunks(self, temp_dir, large_binary_data):
        """
        File lớn (10KB, 10 chunks) → chia + ráp → giống nhau.
        Kiểm tra xử lý file có nhiều chunks không bị sai thứ tự.
        """
        src = os.path.join(temp_dir, "large.bin")
        write_file(src, large_binary_data)

        chunks = list(read_file_chunks(src))
        assert len(chunks) == 10, "10240 bytes / 1024 = 10 chunks đúng"

        dst = os.path.join(temp_dir, "large_copy.bin")
        write_file_from_chunks(dst, chunks)

        assert read_file(dst) == large_binary_data


# ============================================================
# TEST EDGE CASES — TRƯỜNG HỢP BIÊN
# ============================================================

class TestEdgeCases:
    """Test các trường hợp biên — nơi bug thường ẩn nấp."""

    def test_empty_file(self, temp_dir):
        """
        File rỗng (0 bytes) — PHẢI xử lý được.
        Ví dụ: client tạo file rỗng rồi STOR lên server.
        """
        path = os.path.join(temp_dir, "empty.bin")
        write_file(path, b"")

        assert read_file(path) == b""
        assert get_file_size(path) == 0

        chunks = list(read_file_chunks(path))
        assert chunks == [], "File rỗng → 0 chunks"

    def test_single_byte_file(self, temp_dir):
        """File 1 byte — trường hợp nhỏ nhất có dữ liệu."""
        path = os.path.join(temp_dir, "one.bin")
        write_file(path, b"\x42")

        assert read_file(path) == b"\x42"
        chunks = list(read_file_chunks(path))
        assert len(chunks) == 1
        assert chunks[0] == b"\x42"

    def test_file_exactly_one_chunk(self, temp_dir):
        """
        File kích thước = đúng 1 chunk (1024 bytes).
        Trường hợp biên: không có chunk cuối nhỏ hơn.
        """
        data = b"\xAB" * DEFAULT_CHUNK_SIZE  # Đúng 1024 bytes
        path = os.path.join(temp_dir, "exact.bin")
        write_file(path, data)

        chunks = list(read_file_chunks(path))
        assert len(chunks) == 1
        assert len(chunks[0]) == DEFAULT_CHUNK_SIZE

    def test_file_one_byte_over_chunk(self, temp_dir):
        """
        File kích thước = 1 chunk + 1 byte (1025 bytes).
        → 2 chunks: 1 chunk đầy + 1 chunk 1 byte.
        """
        data = b"\xCD" * (DEFAULT_CHUNK_SIZE + 1)
        path = os.path.join(temp_dir, "over.bin")
        write_file(path, data)

        chunks = list(read_file_chunks(path))
        assert len(chunks) == 2
        assert len(chunks[0]) == DEFAULT_CHUNK_SIZE
        assert len(chunks[1]) == 1


# ============================================================
# TEST APPEND
# ============================================================

class TestAppend:
    """Test append_to_file — dùng cho lệnh FTP APPE."""

    def test_append_to_existing(self, temp_dir):
        """Append vào file đã có → nội dung nối tiếp."""
        path = os.path.join(temp_dir, "log.txt")
        write_file(path, b"line1\n")
        append_to_file(path, b"line2\n")

        assert read_file(path) == b"line1\nline2\n"

    def test_append_creates_new_file(self, temp_dir):
        """Append vào file chưa tồn tại → tạo file mới."""
        path = os.path.join(temp_dir, "new.txt")
        append_to_file(path, b"first write")

        assert read_file(path) == b"first write"

    def test_append_binary(self, temp_dir):
        """Append binary data → không bị mất/sửa bytes."""
        path = os.path.join(temp_dir, "data.bin")
        part1 = bytes(range(128))
        part2 = bytes(range(128, 256))
        write_file(path, part1)
        append_to_file(path, part2)

        assert read_file(path) == bytes(range(256))


# ============================================================
# TEST HASH
# ============================================================

class TestHash:
    """
    Test compute_hash — xác minh tính toàn vẹn file.
    Đây là yêu cầu Excellent tier (lệnh HASH).
    """

    def test_sha256_consistency(self, temp_dir, sample_binary_data):
        """Cùng file → cùng hash (gọi 2 lần phải ra kết quả giống nhau)."""
        path = os.path.join(temp_dir, "hash_test.bin")
        write_file(path, sample_binary_data)

        hash1 = compute_hash(path, "sha256")
        hash2 = compute_hash(path, "sha256")

        assert hash1 == hash2, "Cùng file phải cho cùng hash"
        assert len(hash1) == 64, "SHA-256 hex digest luôn 64 ký tự"

    def test_md5_works(self, temp_dir, sample_text_data):
        """MD5 cũng hoạt động đúng."""
        path = os.path.join(temp_dir, "md5_test.txt")
        write_file(path, sample_text_data)

        h = compute_hash(path, "md5")
        assert len(h) == 32, "MD5 hex digest luôn 32 ký tự"

    def test_different_content_different_hash(self, temp_dir):
        """Khác nội dung → khác hash (cực kỳ khó trùng)."""
        path1 = os.path.join(temp_dir, "file1.bin")
        path2 = os.path.join(temp_dir, "file2.bin")
        write_file(path1, b"content A")
        write_file(path2, b"content B")

        assert compute_hash(path1) != compute_hash(path2)

    def test_hash_matches_after_chunk_reassembly(self, temp_dir, sample_binary_data):
        """
        Hash trước khi chia chunks = hash sau khi ráp lại.
        Đây chính xác là luồng verify trong FTP:
          1. Server tính hash file gốc
          2. Gửi file qua UDP (chia chunks)
          3. Client ráp chunks thành file
          4. Client tính hash file nhận được
          5. So sánh → phải giống nhau
        """
        src = os.path.join(temp_dir, "original.bin")
        write_file(src, sample_binary_data)
        hash_before = compute_hash(src)

        # Mô phỏng quá trình chia + ráp
        chunks = list(read_file_chunks(src))
        dst = os.path.join(temp_dir, "received.bin")
        write_file_from_chunks(dst, chunks)
        hash_after = compute_hash(dst)

        assert hash_before == hash_after, "Hash phải giống sau khi chia chunks và ráp lại"

    def test_unsupported_algorithm_raises(self, temp_dir, sample_text_data):
        """Algorithm không hỗ trợ → ValueError."""
        path = os.path.join(temp_dir, "test.txt")
        write_file(path, sample_text_data)

        with pytest.raises(ValueError, match="Unsupported"):
            compute_hash(path, "sha512_not_supported")


# ============================================================
# TEST FILE INFO
# ============================================================

class TestFileInfo:
    """Test get_file_size / file_exists — thông tin file."""

    def test_file_size(self, temp_dir, sample_binary_data):
        """Kích thước file đúng."""
        path = os.path.join(temp_dir, "sized.bin")
        write_file(path, sample_binary_data)

        assert get_file_size(path) == len(sample_binary_data)

    def test_file_exists_true(self, temp_dir):
        """File tồn tại → True."""
        path = os.path.join(temp_dir, "exists.txt")
        write_file(path, b"data")

        assert file_exists(path) is True

    def test_file_exists_false(self, temp_dir):
        """File không tồn tại → False."""
        assert file_exists(os.path.join(temp_dir, "nope.txt")) is False

    def test_file_exists_directory_returns_false(self, temp_dir):
        """
        Path trỏ đến thư mục → False.
        Phân biệt file vs directory quan trọng cho lệnh SIZE, RETR, DELE...
        """
        assert file_exists(temp_dir) is False
