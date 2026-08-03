"""
dir_manager.py — Quản lý filesystem phía server, chặn path traversal

=== FILE NÀY GIẢI QUYẾT GÌ? ===
Cung cấp tất cả thao tác thư mục/file metadata cho FTP server:
  - Validate path: đảm bảo client không thoát khỏi thư mục gốc FTP
  - Resolve path: chuyển đường dẫn relative → absolute an toàn
  - List directory: trả danh sách file/thư mục với metadata
  - Tạo/xoá thư mục

Mọi thao tác filesystem trong server PHẢI đi qua module này.
Không bao giờ gọi os.listdir(), os.chdir(), os.makedirs()... trực tiếp từ handler.

=== KẾT NỐI VỚI FILE NÀO? ===
  - server/threaded_server.py  → handler gọi khi xử lý CWD, LIST, MKD, RMD...
  - Role A's session            → session lưu working directory, dir_manager resolve path dựa trên đó
  - common/file_handler.py      → dir_manager validate path trước, rồi file_handler đọc/ghi file

=== XOÁ FILE NÀY THÌ GÌ HỎNG? ===
  - Tất cả lệnh PWD, CWD, CDUP, MKD, RMD, LIST, NLST, STAT, MDTM đều chết
  - Nghiêm trọng hơn: nếu không validate, client có thể đọc/ghi BẤT KỲ file nào trên server
    (path traversal attack — lỗ hổng bảo mật cổ điển)
"""

import os
import stat
import time


# ============================================================
# VALIDATE PATH — Chặn path traversal
# ============================================================

def validate_path(base_dir: str, target_path: str) -> bool:
    """
    Kiểm tra target_path có nằm trong base_dir (sandbox FTP) hay không.

    Cách hoạt động:
      1. os.path.realpath(base_dir): resolve symlink + normalize base
         Ví dụ: /srv/ftp → /srv/ftp (hoặc /mnt/data/ftp nếu là symlink)

      2. os.path.realpath(target_path): resolve symlink + "../" trong target
         Ví dụ: /srv/ftp/docs/../../etc → /etc

      3. So sánh: real_target bắt đầu bằng real_base?
         /etc.startswith(/srv/ftp) → False → ❌ BLOCKED
         /srv/ftp/docs.startswith(/srv/ftp) → True → ✅ OK

    Tại sao dùng realpath() thay vì abspath()?
      - abspath() chỉ xử lý ".." bằng cách nối chuỗi, KHÔNG resolve symlink
      - Ví dụ: nếu /srv/ftp/link → /etc (symlink), thì:
        - abspath("/srv/ftp/link") = "/srv/ftp/link" → tưởng an toàn (SAI!)
        - realpath("/srv/ftp/link") = "/etc" → phát hiện thoát sandbox (ĐÚNG!)

    Tại sao thêm os.sep vào cuối real_base?
      - Tránh false positive: base = "/srv/ftp", target = "/srv/ftp_backup"
        - "/srv/ftp_backup".startswith("/srv/ftp") → True → SAI! (không phải thư mục con)
        - "/srv/ftp_backup".startswith("/srv/ftp/") → False → ĐÚNG
      - Ngoại trừ khi target == base (client ở đúng root) → cho phép

    Args:
        base_dir: Thư mục gốc FTP (sandbox boundary)
        target_path: Đường dẫn cần kiểm tra

    Returns:
        bool: True nếu target nằm trong hoặc bằng base_dir
    """
    # Resolve tất cả symlink và ".." để lấy đường dẫn thật
    real_base = os.path.realpath(base_dir)
    real_target = os.path.realpath(target_path)

    # Trường hợp target = chính base dir (client ở root FTP)
    if real_target == real_base:
        return True

    # Kiểm tra target là con của base (thêm sep để tránh /ftp vs /ftp_backup)
    return real_target.startswith(real_base + os.sep)


# ============================================================
# RESOLVE PATH — Chuyển relative → absolute an toàn
# ============================================================

def resolve_path(base_dir: str, cwd: str, relative_path: str) -> str:
    """
    Chuyển đường dẫn relative từ client thành absolute path an toàn.

    Cách hoạt động:
      1. Nếu relative_path là absolute (bắt đầu bằng /) → join với base_dir
         Ví dụ: base="/srv/ftp", relative="/docs" → "/srv/ftp/docs"

      2. Nếu relative_path là relative → join với cwd
         Ví dụ: cwd="/srv/ftp/docs", relative="reports" → "/srv/ftp/docs/reports"

      3. Validate kết quả → nếu thoát sandbox thì raise PermissionError

    Tại sao return path đã resolve thay vì chỉ validate?
      - Caller không cần tự join path (dễ sai)
      - Đảm bảo path luôn đã qua validate
      - Single point of truth: mọi path đều đi qua hàm này

    Ví dụ sử dụng (trong command handler):
      # Client gửi: CWD reports
      new_cwd = resolve_path(FTP_ROOT, session.cwd, "reports")
      # → "/srv/ftp/docs/reports" (nếu hợp lệ)
      # → PermissionError (nếu thoát sandbox)

    Args:
        base_dir: Thư mục gốc FTP
        cwd: Thư mục hiện tại của session (absolute path)
        relative_path: Đường dẫn client gửi lên (có thể relative hoặc absolute)

    Returns:
        str: Absolute path đã validate, an toàn

    Raises:
        PermissionError: Nếu path cố thoát khỏi sandbox
    """
    if not relative_path:
        # Client gửi lệnh không có argument (ví dụ: LIST không có path)
        # → trả về cwd hiện tại
        resolved_cwd = os.path.realpath(cwd)
        if not validate_path(base_dir, resolved_cwd):
            raise PermissionError("Current directory is outside the FTP root.")
        return resolved_cwd

    # Kiểm tra path có phải "absolute" theo góc nhìn FTP không.
    # FTP client luôn gửi đường dẫn kiểu Unix: "/docs", "/images/photo.jpg"
    # Trên Windows, os.path.isabs("/docs") = False (cần drive letter C:\)
    # → phải kiểm tra thêm: bắt đầu bằng "/" cũng coi là absolute trong FTP
    is_absolute = os.path.isabs(relative_path) or relative_path.startswith("/")

    if is_absolute:
        # Path absolute: client gửi "/docs" → hiểu là "<base>/docs"
        # Bỏ "/" và "\" đầu tiên rồi join với base_dir
        # Nếu không bỏ, os.path.join(base, "/docs") = "/docs" (Python bỏ base!)
        stripped = relative_path.lstrip("/\\")
        resolved = os.path.join(base_dir, stripped)
    else:
        # Path relative: client gửi "reports" → join với cwd
        resolved = os.path.join(cwd, relative_path)

    # Resolve symlink + normalize
    resolved = os.path.realpath(resolved)

    # Validate: phải nằm trong sandbox
    if not validate_path(base_dir, resolved):
        raise PermissionError(
            f"Access denied: path '{relative_path}' is outside the FTP root directory."
        )

    return resolved


# ============================================================
# LIST DIRECTORY — Danh sách file/thư mục
# ============================================================

def list_directory(path: str, base_dir: str | None = None) -> list:
    """
    Trả về danh sách chi tiết file/thư mục trong path.

    Cách hoạt động:
      1. Dùng os.scandir(path) thay vì os.listdir(path)
         - scandir trả về DirEntry objects — đã có metadata sẵn (type, stat)
         - listdir chỉ trả tên → phải gọi os.stat() cho từng file → chậm gấp đôi
         - Với thư mục 1000 files: scandir ≈ 1 syscall, listdir+stat ≈ 2001 syscalls

      2. Với mỗi entry, thu thập:
         - name: tên file/thư mục
         - size: kích thước (bytes), 0 nếu là thư mục
         - type: "file" hoặc "dir"
         - permissions: chuỗi rwx (ví dụ: "rwxr-xr-x")
         - modified: thời gian sửa cuối (YYYYMMDDhhmmss — format FTP chuẩn cho MDTM)

      3. Sắp xếp: thư mục trước, file sau. Trong mỗi nhóm sắp xếp theo tên.

    Dùng cho lệnh FTP LIST:
      Client gửi: LIST
      Server trả: 150 Opening data connection
                  drwxr-xr-x    4096  20260724103000  documents
                  -rw-r--r--   15360  20260723090000  report.pdf
                  226 Transfer complete

    Args:
        path: Đường dẫn thư mục cần liệt kê (đã validate)

    Returns:
        list[dict]: Danh sách dict, mỗi dict chứa thông tin 1 entry
                    Keys: name, size, type, permissions, modified

    Raises:
        NotADirectoryError: Nếu path không phải thư mục
        FileNotFoundError: Nếu path không tồn tại
    """
    if not os.path.isdir(path):
        if os.path.exists(path):
            raise NotADirectoryError(f"Not a directory: '{path}'")
        raise FileNotFoundError(f"Directory not found: '{path}'")

    entries = []

    # os.scandir() trả về iterator of DirEntry — hiệu quả hơn listdir()
    with os.scandir(path) as scanner:
        for entry in scanner:
            try:
                if base_dir is not None and not validate_path(base_dir, entry.path):
                    # Không để symlink trong FTP root làm lộ metadata bên ngoài root.
                    continue
                entry_stat = entry.stat()

                entries.append({
                    "name": entry.name,
                    "size": entry_stat.st_size if entry.is_file() else 0,
                    "type": "dir" if entry.is_dir() else "file",
                    "permissions": _format_permissions(entry_stat.st_mode),
                    "modified": _format_mtime(entry_stat.st_mtime),
                })
            except (PermissionError, OSError):
                # Bỏ qua file không có quyền đọc — vẫn list được phần còn lại
                continue

    # Sắp xếp: thư mục trước, sau đó theo tên (case-insensitive)
    entries.sort(key=lambda e: (e["type"] != "dir", e["name"].lower()))

    return entries


def list_names(path: str, base_dir: str | None = None) -> list:
    """
    Trả về danh sách TÊN file/thư mục (chỉ tên, không metadata).

    Dùng cho lệnh FTP NLST (Name List):
      Client gửi: NLST
      Server trả: documents
                  report.pdf
                  notes.txt

    Khác LIST ở chỗ: không có size, permissions, modified — chỉ tên.
    NLST thường dùng cho scripts/automation (dễ parse hơn LIST).

    Args:
        path: Đường dẫn thư mục (đã validate)

    Returns:
        list[str]: Danh sách tên, sắp xếp theo alphabet
    """
    if not os.path.isdir(path):
        if os.path.exists(path):
            raise NotADirectoryError(f"Not a directory: '{path}'")
        raise FileNotFoundError(f"Directory not found: '{path}'")

    with os.scandir(path) as scanner:
        names = [
            entry.name
            for entry in scanner
            if base_dir is None or validate_path(base_dir, entry.path)
        ]
    names.sort(key=str.lower)
    return names


# ============================================================
# TẠO / XOÁ THƯ MỤC
# ============================================================

def make_directory(base_dir: str, path: str) -> str:
    """
    Tạo thư mục mới, validate trước để đảm bảo trong sandbox.

    Cách hoạt động:
      1. Validate path → chặn nếu cố tạo thư mục ngoài FTP root
      2. Kiểm tra đã tồn tại chưa → nếu có thì báo lỗi (FTP không tự overwrite)
      3. os.makedirs(path) — tạo thư mục (kể cả cha nếu cần)

    Dùng cho lệnh MKD:
      Client: MKD reports
      Server: 257 "/documents/reports" created

    Args:
        base_dir: Thư mục gốc FTP (sandbox)
        path: Đường dẫn thư mục cần tạo (đã resolve bằng resolve_path)

    Returns:
        str: Đường dẫn tuyệt đối thư mục đã tạo

    Raises:
        PermissionError: Path ngoài sandbox
        FileExistsError: Thư mục đã tồn tại
    """
    if not validate_path(base_dir, os.path.dirname(path)):
        raise PermissionError(
            f"Access denied: cannot create directory outside FTP root."
        )

    if os.path.exists(path):
        raise FileExistsError(f"Directory already exists: '{path}'")

    os.makedirs(path)
    return os.path.realpath(path)


def remove_directory(base_dir: str, path: str) -> None:
    """
    Xoá thư mục RỖNG, validate trước.

    Cách hoạt động:
      1. Validate path → chặn xoá ngoài sandbox
      2. Kiểm tra tồn tại + là thư mục
      3. os.rmdir(path) — CHỈ xoá nếu rỗng

    Tại sao chỉ xoá rỗng?
      - Đúng spec FTP (RFC 959): RMD chỉ xoá thư mục rỗng
      - An toàn: tránh xoá nhầm cả cây thư mục lớn
      - Nếu client muốn xoá thư mục có file → phải DELE từng file trước

    Dùng cho lệnh RMD:
      Client: RMD old_reports
      Server: 250 Directory removed (nếu rỗng)
      Server: 550 Directory not empty (nếu còn file)

    Args:
        base_dir: Thư mục gốc FTP
        path: Đường dẫn thư mục cần xoá (đã resolve)

    Raises:
        PermissionError: Path ngoài sandbox hoặc cố xoá FTP root
        FileNotFoundError: Thư mục không tồn tại
        NotADirectoryError: Path là file, không phải thư mục
        OSError: Thư mục không rỗng
    """
    if not validate_path(base_dir, path):
        raise PermissionError(
            f"Access denied: cannot remove directory outside FTP root."
        )

    # Không cho xoá chính FTP root
    if os.path.realpath(path) == os.path.realpath(base_dir):
        raise PermissionError("Cannot remove the FTP root directory.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: '{path}'")

    if not os.path.isdir(path):
        raise NotADirectoryError(f"Not a directory: '{path}'")

    # os.rmdir() chỉ xoá thư mục rỗng — raise OSError nếu còn file
    os.rmdir(path)


# ============================================================
# THÔNG TIN FILE — Cho lệnh STAT, MDTM, SIZE, DELE, RNFR/RNTO
# ============================================================

def get_entry_info(path: str, base_dir: str | None = None) -> dict:
    """
    Trả về metadata của 1 file hoặc thư mục.

    Dùng cho:
      - STAT <path>: trả thông tin chi tiết
      - MDTM <file>: trả thời gian sửa cuối

    Args:
        path: Đường dẫn (đã validate)

    Returns:
        dict: {name, size, type, permissions, modified}
    """
    if base_dir is not None and not validate_path(base_dir, path):
        raise PermissionError("Access denied: path outside FTP root.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: '{path}'")

    s = os.stat(path)
    return {
        "name": os.path.basename(path),
        "size": s.st_size,
        "type": "dir" if os.path.isdir(path) else "file",
        "permissions": _format_permissions(s.st_mode),
        "modified": _format_mtime(s.st_mtime),
    }


def delete_file(base_dir: str, path: str) -> None:
    """
    Xoá 1 file, validate trước.

    Dùng cho lệnh DELE:
      Client: DELE old_report.pdf
      Server: 250 File deleted

    Args:
        base_dir: Thư mục gốc FTP
        path: Đường dẫn file cần xoá (đã resolve)

    Raises:
        PermissionError: Path ngoài sandbox
        FileNotFoundError: File không tồn tại
        IsADirectoryError: Path là thư mục (dùng RMD thay vì DELE)
    """
    if not validate_path(base_dir, path):
        raise PermissionError("Access denied: path outside FTP root.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: '{path}'")

    if os.path.isdir(path):
        raise IsADirectoryError(
            f"'{path}' is a directory. Use RMD to remove directories."
        )

    os.remove(path)


def rename_entry(base_dir: str, old_path: str, new_path: str) -> None:
    """
    Đổi tên file hoặc thư mục (RNFR + RNTO).

    Cách hoạt động:
      1. Validate CẢ HAI path (cũ và mới) đều trong sandbox
      2. Kiểm tra old_path tồn tại
      3. Kiểm tra new_path chưa tồn tại (tránh ghi đè nhầm)
      4. os.rename(old, new)

    Dùng cho lệnh RNFR/RNTO:
      Client: RNFR old_name.txt   → Server: 350 Ready for RNTO
      Client: RNTO new_name.txt   → Server: 250 Rename successful

    Args:
        base_dir: Thư mục gốc FTP
        old_path: Đường dẫn cũ (đã resolve)
        new_path: Đường dẫn mới (đã resolve)

    Raises:
        PermissionError: Path ngoài sandbox
        FileNotFoundError: old_path không tồn tại
        FileExistsError: new_path đã tồn tại
    """
    if not validate_path(base_dir, old_path):
        raise PermissionError("Access denied: source path outside FTP root.")
    if not validate_path(base_dir, new_path):
        raise PermissionError("Access denied: destination path outside FTP root.")

    if not os.path.exists(old_path):
        raise FileNotFoundError(f"Source not found: '{old_path}'")
    if os.path.exists(new_path):
        raise FileExistsError(f"Destination already exists: '{new_path}'")

    os.rename(old_path, new_path)


# ============================================================
# HELPER FUNCTIONS — Hàm nội bộ (tiền tố _ = không dùng bên ngoài)
# ============================================================

def _format_permissions(mode: int) -> str:
    """
    Chuyển số mode (ví dụ: 0o755) thành chuỗi rwx (ví dụ: "rwxr-xr-x").

    Cách hoạt động:
      - mode là bitmask: mỗi bit đại diện 1 quyền
      - stat.S_IRUSR = bit read cho owner, stat.S_IWUSR = write, stat.S_IXUSR = execute
      - Tương tự cho group (GRP) và others (OTH)
      - Kiểm tra từng bit: nếu bật → ký tự tương ứng, nếu tắt → "-"

    Ví dụ:
      0o755 → rwxr-xr-x (owner: full, group: read+exec, others: read+exec)
      0o644 → rw-r--r-- (owner: read+write, others: read only)
    """
    perms = ""
    perms += "r" if mode & stat.S_IRUSR else "-"
    perms += "w" if mode & stat.S_IWUSR else "-"
    perms += "x" if mode & stat.S_IXUSR else "-"
    perms += "r" if mode & stat.S_IRGRP else "-"
    perms += "w" if mode & stat.S_IWGRP else "-"
    perms += "x" if mode & stat.S_IXGRP else "-"
    perms += "r" if mode & stat.S_IROTH else "-"
    perms += "w" if mode & stat.S_IWOTH else "-"
    perms += "x" if mode & stat.S_IXOTH else "-"
    return perms


def _format_mtime(timestamp: float) -> str:
    """
    Chuyển Unix timestamp thành chuỗi FTP chuẩn: YYYYMMDDhhmmss.

    Đây là format bắt buộc cho lệnh MDTM (RFC 3659):
      Client: MDTM report.pdf
      Server: 213 20260724103000

    Ví dụ:
      1753346400.0 → "20260724103000" (24/07/2026 10:30:00)

    Args:
        timestamp: Unix timestamp (float, từ os.stat().st_mtime)

    Returns:
        str: Chuỗi 14 ký tự YYYYMMDDhhmmss
    """
    return time.strftime("%Y%m%d%H%M%S", time.localtime(timestamp))
