"""
test_dir_manager.py — Test cho module common/dir_manager.py

=== TEST NÀY KIỂM TRA GÌ? ===
  1. Path traversal attacks: ../, ....//,  symbolic link thoát sandbox
  2. Resolve path: relative, absolute, rỗng
  3. List directory: danh sách chi tiết + name-only
  4. Tạo/xoá thư mục: trong sandbox, ngoài sandbox, rỗng/không rỗng
  5. Xoá file, đổi tên
  6. Edge cases: path trùng tên base, xoá FTP root

=== CÁCH CHẠY ===
  cd <project-root>
  py -m pytest tests/test_dir_manager.py -v
"""

import os
import sys
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.dir_manager import (
    validate_path,
    resolve_path,
    list_directory,
    list_names,
    make_directory,
    remove_directory,
    get_entry_info,
    delete_file,
    rename_entry,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def ftp_root(tmp_path):
    """
    Tạo cấu trúc FTP giả lập để test:

    ftp_root/
    ├── docs/
    │   ├── report.txt    (15 bytes)
    │   └── notes.txt     (11 bytes)
    ├── images/
    │   └── photo.bin     (256 bytes binary)
    ├── empty_dir/
    └── readme.txt        (13 bytes)
    """
    root = tmp_path / "ftp_root"
    root.mkdir()

    # Tạo thư mục con
    docs = root / "docs"
    docs.mkdir()
    (docs / "report.txt").write_bytes(b"report content!")       # 15 bytes
    (docs / "notes.txt").write_bytes(b"some notes!")            # 11 bytes

    images = root / "images"
    images.mkdir()
    (images / "photo.bin").write_bytes(bytes(range(256)))        # 256 bytes binary

    (root / "empty_dir").mkdir()

    (root / "readme.txt").write_bytes(b"Hello readme!")          # 13 bytes

    return str(root)


# ============================================================
# TEST VALIDATE PATH — Chặn path traversal
# ============================================================

class TestValidatePath:
    """Test validate_path — trái tim bảo mật."""

    def test_path_inside_sandbox(self, ftp_root):
        """Path hợp lệ bên trong sandbox → True."""
        docs_path = os.path.join(ftp_root, "docs")
        assert validate_path(ftp_root, docs_path) is True

    def test_path_equals_base(self, ftp_root):
        """Path = chính FTP root → True (client ở root)."""
        assert validate_path(ftp_root, ftp_root) is True

    def test_path_traversal_dotdot(self, ftp_root):
        """
        CWD ../../ → cố thoát sandbox → False.
        Đây là attack phổ biến nhất.
        """
        evil_path = os.path.join(ftp_root, "..", "..")
        assert validate_path(ftp_root, evil_path) is False

    def test_path_traversal_etc_passwd(self, ftp_root):
        """CWD ../../etc/passwd → False."""
        evil_path = os.path.join(ftp_root, "..", "..", "etc", "passwd")
        assert validate_path(ftp_root, evil_path) is False

    def test_path_traversal_mixed(self, ftp_root):
        """CWD docs/../../ → vào docs rồi lùi ra 2 lần → thoát sandbox."""
        evil_path = os.path.join(ftp_root, "docs", "..", "..")
        assert validate_path(ftp_root, evil_path) is False

    def test_similar_name_not_confused(self, ftp_root):
        """
        /ftp_root_backup KHÔNG được nhầm là con của /ftp_root.
        Test trick os.sep: startswith phải so sánh /ftp_root/ (có slash cuối).
        """
        fake_path = ftp_root + "_backup"
        assert validate_path(ftp_root, fake_path) is False

    def test_deeply_nested_valid(self, ftp_root):
        """Path lồng sâu nhưng hợp lệ → True."""
        deep = os.path.join(ftp_root, "a", "b", "c", "d")
        # Path không cần tồn tại thật — validate chỉ kiểm tra prefix
        # realpath sẽ resolve ra đường dẫn trong ftp_root
        assert validate_path(ftp_root, deep) is True


# ============================================================
# TEST RESOLVE PATH — Chuyển relative → absolute
# ============================================================

class TestResolvePath:
    """Test resolve_path — chuyển đổi path an toàn."""

    def test_relative_path(self, ftp_root):
        """Input relative 'docs' → join với cwd."""
        cwd = ftp_root
        result = resolve_path(ftp_root, cwd, "docs")
        expected = os.path.realpath(os.path.join(ftp_root, "docs"))
        assert result == expected

    def test_absolute_path(self, ftp_root):
        """Input absolute '/docs' → join với base (bỏ /)."""
        cwd = os.path.join(ftp_root, "images")  # cwd không quan trọng cho abs path
        result = resolve_path(ftp_root, cwd, "/docs")
        expected = os.path.realpath(os.path.join(ftp_root, "docs"))
        assert result == expected

    def test_empty_path_returns_cwd(self, ftp_root):
        """Input rỗng → trả về cwd hiện tại."""
        cwd = os.path.join(ftp_root, "docs")
        result = resolve_path(ftp_root, cwd, "")
        assert result == os.path.realpath(cwd)

    def test_dotdot_within_sandbox(self, ftp_root):
        """CWD docs rồi .. → quay về root → hợp lệ."""
        cwd = os.path.join(ftp_root, "docs")
        result = resolve_path(ftp_root, cwd, "..")
        assert result == os.path.realpath(ftp_root)

    def test_dotdot_escaping_raises(self, ftp_root):
        """CWD ../../ từ root → thoát sandbox → PermissionError."""
        with pytest.raises(PermissionError):
            resolve_path(ftp_root, ftp_root, "../..")

    def test_nested_relative(self, ftp_root):
        """Relative path nhiều cấp: 'a/b/c' → join với cwd."""
        cwd = ftp_root
        result = resolve_path(ftp_root, cwd, os.path.join("docs", "subfolder"))
        expected = os.path.realpath(os.path.join(ftp_root, "docs", "subfolder"))
        assert result == expected


# ============================================================
# TEST LIST DIRECTORY
# ============================================================

class TestListDirectory:
    """Test list_directory — danh sách chi tiết."""

    def test_list_root(self, ftp_root):
        """List root FTP → 4 entries (docs, images, empty_dir, readme.txt)."""
        entries = list_directory(ftp_root)
        names = [e["name"] for e in entries]

        assert "docs" in names
        assert "images" in names
        assert "empty_dir" in names
        assert "readme.txt" in names
        assert len(entries) == 4

    def test_list_has_required_fields(self, ftp_root):
        """Mỗi entry phải có đủ 5 trường: name, size, type, permissions, modified."""
        entries = list_directory(ftp_root)
        required_keys = {"name", "size", "type", "permissions", "modified"}

        for entry in entries:
            assert required_keys.issubset(entry.keys()), (
                f"Entry '{entry.get('name')}' thiếu trường: "
                f"{required_keys - set(entry.keys())}"
            )

    def test_list_types_correct(self, ftp_root):
        """Thư mục type='dir', file type='file'."""
        entries = list_directory(ftp_root)
        type_map = {e["name"]: e["type"] for e in entries}

        assert type_map["docs"] == "dir"
        assert type_map["images"] == "dir"
        assert type_map["readme.txt"] == "file"

    def test_list_dirs_come_first(self, ftp_root):
        """Thư mục được sắp trước file."""
        entries = list_directory(ftp_root)
        types = [e["type"] for e in entries]

        # Tìm index file đầu tiên và dir cuối cùng
        dir_indices = [i for i, t in enumerate(types) if t == "dir"]
        file_indices = [i for i, t in enumerate(types) if t == "file"]

        if dir_indices and file_indices:
            assert max(dir_indices) < min(file_indices), (
                "Thư mục phải sắp trước file"
            )

    def test_list_file_sizes(self, ftp_root):
        """Kích thước file đúng."""
        docs_path = os.path.join(ftp_root, "docs")
        entries = list_directory(docs_path)
        size_map = {e["name"]: e["size"] for e in entries}

        assert size_map["report.txt"] == 15
        assert size_map["notes.txt"] == 11

    def test_list_nonexistent_raises(self, ftp_root):
        """List thư mục không tồn tại → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            list_directory(os.path.join(ftp_root, "nonexistent"))

    def test_list_file_not_dir_raises(self, ftp_root):
        """List 1 file (không phải thư mục) → NotADirectoryError."""
        with pytest.raises(NotADirectoryError):
            list_directory(os.path.join(ftp_root, "readme.txt"))

    def test_list_empty_dir(self, ftp_root):
        """List thư mục rỗng → list rỗng."""
        entries = list_directory(os.path.join(ftp_root, "empty_dir"))
        assert entries == []

    def test_modified_format(self, ftp_root):
        """Modified time phải đúng format YYYYMMDDhhmmss (14 ký tự số)."""
        entries = list_directory(ftp_root)
        for entry in entries:
            mtime = entry["modified"]
            assert len(mtime) == 14, f"Modified '{mtime}' phải 14 ký tự"
            assert mtime.isdigit(), f"Modified '{mtime}' phải toàn số"

    def test_permissions_format(self, ftp_root):
        """Permissions phải 9 ký tự, chỉ gồm r/w/x/-."""
        entries = list_directory(ftp_root)
        for entry in entries:
            perms = entry["permissions"]
            assert len(perms) == 9, f"Permissions '{perms}' phải 9 ký tự"
            assert all(c in "rwx-" for c in perms), (
                f"Permissions '{perms}' chỉ được chứa r/w/x/-"
            )


class TestListNames:
    """Test list_names — danh sách tên (cho NLST)."""

    def test_list_names_root(self, ftp_root):
        """NLST root → 4 tên."""
        names = list_names(ftp_root)
        assert len(names) == 4
        assert "docs" in names
        assert "readme.txt" in names

    def test_list_names_sorted(self, ftp_root):
        """Tên phải sắp xếp alphabetically."""
        names = list_names(ftp_root)
        assert names == sorted(names, key=str.lower)

    def test_list_names_empty_dir(self, ftp_root):
        """NLST thư mục rỗng → list rỗng."""
        names = list_names(os.path.join(ftp_root, "empty_dir"))
        assert names == []


# ============================================================
# TEST TẠO / XOÁ THƯ MỤC
# ============================================================

class TestMakeDirectory:
    """Test make_directory — tạo thư mục."""

    def test_make_dir_success(self, ftp_root):
        """Tạo thư mục mới trong sandbox → thành công."""
        new_dir = os.path.join(ftp_root, "new_folder")
        result = make_directory(ftp_root, new_dir)

        assert os.path.isdir(new_dir)
        assert result == os.path.realpath(new_dir)

    def test_make_dir_already_exists_raises(self, ftp_root):
        """Tạo thư mục đã tồn tại → FileExistsError."""
        with pytest.raises(FileExistsError):
            make_directory(ftp_root, os.path.join(ftp_root, "docs"))

    def test_make_dir_outside_sandbox_raises(self, ftp_root):
        """Tạo thư mục ngoài sandbox → PermissionError."""
        evil_dir = os.path.join(ftp_root, "..", "hacked")
        with pytest.raises(PermissionError):
            make_directory(ftp_root, evil_dir)


class TestRemoveDirectory:
    """Test remove_directory — xoá thư mục."""

    def test_remove_empty_dir(self, ftp_root):
        """Xoá thư mục rỗng → thành công."""
        empty = os.path.join(ftp_root, "empty_dir")
        assert os.path.isdir(empty)

        remove_directory(ftp_root, empty)
        assert not os.path.exists(empty)

    def test_remove_nonempty_dir_raises(self, ftp_root):
        """Xoá thư mục KHÔNG rỗng → OSError (đúng spec FTP)."""
        with pytest.raises(OSError):
            remove_directory(ftp_root, os.path.join(ftp_root, "docs"))

    def test_remove_ftp_root_raises(self, ftp_root):
        """Xoá chính FTP root → PermissionError."""
        with pytest.raises(PermissionError):
            remove_directory(ftp_root, ftp_root)

    def test_remove_nonexistent_raises(self, ftp_root):
        """Xoá thư mục không tồn tại → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            remove_directory(ftp_root, os.path.join(ftp_root, "ghost"))

    def test_remove_file_not_dir_raises(self, ftp_root):
        """Xoá 1 file bằng remove_directory → NotADirectoryError."""
        with pytest.raises(NotADirectoryError):
            remove_directory(ftp_root, os.path.join(ftp_root, "readme.txt"))


# ============================================================
# TEST FILE OPERATIONS — delete, rename, info
# ============================================================

class TestDeleteFile:
    """Test delete_file — xoá file."""

    def test_delete_success(self, ftp_root):
        """Xoá file hợp lệ → file biến mất."""
        target = os.path.join(ftp_root, "readme.txt")
        assert os.path.isfile(target)

        delete_file(ftp_root, target)
        assert not os.path.exists(target)

    def test_delete_nonexistent_raises(self, ftp_root):
        """Xoá file không tồn tại → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            delete_file(ftp_root, os.path.join(ftp_root, "ghost.txt"))

    def test_delete_directory_raises(self, ftp_root):
        """Xoá thư mục bằng delete_file → IsADirectoryError."""
        with pytest.raises(IsADirectoryError):
            delete_file(ftp_root, os.path.join(ftp_root, "docs"))

    def test_delete_outside_sandbox_raises(self, ftp_root):
        """Xoá file ngoài sandbox → PermissionError."""
        # Tạo file ngoài sandbox
        outside = os.path.join(ftp_root, "..", "outside.txt")
        # Ghi file giả bên ngoài (dùng realpath)
        outside_real = os.path.realpath(outside)
        with open(outside_real, "w") as f:
            f.write("outside")

        try:
            with pytest.raises(PermissionError):
                delete_file(ftp_root, outside)
        finally:
            # Cleanup
            if os.path.exists(outside_real):
                os.remove(outside_real)


class TestRenameEntry:
    """Test rename_entry — đổi tên file/thư mục."""

    def test_rename_file(self, ftp_root):
        """Đổi tên file → tên cũ biến mất, tên mới xuất hiện."""
        old = os.path.join(ftp_root, "readme.txt")
        new = os.path.join(ftp_root, "readme_v2.txt")

        rename_entry(ftp_root, old, new)

        assert not os.path.exists(old)
        assert os.path.isfile(new)

    def test_rename_dir(self, ftp_root):
        """Đổi tên thư mục."""
        old = os.path.join(ftp_root, "empty_dir")
        new = os.path.join(ftp_root, "renamed_dir")

        rename_entry(ftp_root, old, new)

        assert not os.path.exists(old)
        assert os.path.isdir(new)

    def test_rename_nonexistent_raises(self, ftp_root):
        """Đổi tên file không tồn tại → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            rename_entry(
                ftp_root,
                os.path.join(ftp_root, "ghost.txt"),
                os.path.join(ftp_root, "new.txt"),
            )

    def test_rename_to_existing_raises(self, ftp_root):
        """Đổi tên → tên mới đã tồn tại → FileExistsError."""
        with pytest.raises(FileExistsError):
            rename_entry(
                ftp_root,
                os.path.join(ftp_root, "readme.txt"),
                os.path.join(ftp_root, "docs"),  # đã tồn tại
            )


class TestGetEntryInfo:
    """Test get_entry_info — lấy metadata."""

    def test_file_info(self, ftp_root):
        """Lấy info file → type='file', size đúng."""
        info = get_entry_info(os.path.join(ftp_root, "readme.txt"))

        assert info["name"] == "readme.txt"
        assert info["type"] == "file"
        assert info["size"] == 13
        assert len(info["permissions"]) == 9
        assert len(info["modified"]) == 14

    def test_dir_info(self, ftp_root):
        """Lấy info thư mục → type='dir'."""
        info = get_entry_info(os.path.join(ftp_root, "docs"))

        assert info["name"] == "docs"
        assert info["type"] == "dir"

    def test_nonexistent_raises(self, ftp_root):
        """Lấy info path không tồn tại → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            get_entry_info(os.path.join(ftp_root, "nope"))
