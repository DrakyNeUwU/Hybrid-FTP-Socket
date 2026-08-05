# GenAI Usage Log — Role C (Khanh, Integration Lead)

## July 26, 2026 — File Handler (`common/file_handler.py`)

**Exact prompt:**
> "Viết module đọc/ghi file binary an toàn trong Python dùng cho dự án FTP. Cần chia nhỏ file thành chunks 1024 bytes bằng generator, ráp chunks thành file, ghi đè, append file và tính hash SHA-256/MD5 của file."

**English translation:**
> "Write a safe binary file read/write module in Python for an FTP project. It must split files into 1,024-byte chunks with a generator, reassemble chunks, overwrite and append files, and calculate SHA-256/MD5 hashes."

**Raw GenAI output:**

The initial suggestion used `open(path, "r")`, calculated small-file hashes with
`hashlib.sha256(f.read()).hexdigest()`, and used `os.path.abspath()` for path
validation.

**Review and refinement:**

- Text mode (`"r"`) can change line endings on Windows and corrupt images,
  archives, or videos. All file operations were changed to binary modes:
  `"rb"`, `"wb"`, and `"ab"`.
- Reading an entire large file into memory just to hash it is wasteful. The
  implementation now reads chunks and calls `hash.update(chunk)`, keeping memory
  use approximately equal to one chunk.

## July 27, 2026 — Directory Manager and Path-Traversal Protection

**Exact prompt:**
> "Viết hàm Python kiểm tra an toàn một đường dẫn đầu vào từ Client để tránh lỗ hổng Path Traversal (`../../etc/passwd`). Hàm cần kiểm tra đường dẫn đó có nằm trong thư mục gốc FTP (sandbox) hay không."

**English translation:**
> "Write a Python function that safely validates a client-supplied path to prevent path traversal (`../../etc/passwd`). The function must verify that the path remains inside the FTP root sandbox."

**Raw GenAI output:**

```python
def validate_path(base, target):
    return os.path.abspath(target).startswith(os.path.abspath(base))
```

**Review and refinement:**

- `abspath()` does not resolve symbolic links. It was replaced with
  `realpath()` so a link inside the FTP root cannot point to an outside file.
- A plain prefix check incorrectly accepts `/srv/ftp_backup` for the root
  `/srv/ftp`. The comparison now includes `os.sep`, while still allowing the
  root path itself.
- Directory listings use `os.scandir()` so entry metadata can be read without
  repeatedly looking up every filename.

## July 28, 2026 — Multithreaded TCP Server

**Exact prompt:**
> "Viết socket server đa luồng bằng Python (threading). Server cần lắng nghe kết nối, tạo thread riêng cho mỗi client, theo dõi danh sách active clients thread-safe và có cơ chế stop server không bị dính treo."

**English translation:**
> "Write a multithreaded socket server using Python threading. It must listen for connections, create a separate thread per client, track active clients safely, and stop without hanging."

**Raw GenAI output:**

The initial version used a `threading.Thread` subclass and a permanent
`while True: client, address = server.accept()` loop without a timeout.

**Review and refinement:**

- Blocking `accept()` and `recv()` calls prevented a prompt shutdown. Both
  sockets now use a 0.5-second timeout and periodically check a running flag.
- Locks protect the active-client registry and console logging from concurrent
  writes.

## July 30, 2026 — CLI Display (`client/cli_display.py`)

**Exact prompt:**
> "Viết module hiển thị CLI đẹp bằng Python: format dung lượng bytes ra KB/MB/GB, thanh tiến trình transfer bar dạng `[████░░░░] 50%` và bảng danh sách thư mục."

**English translation:**
> "Write a clear Python CLI display module that formats bytes as KB/MB/GB, displays a transfer bar such as `[████░░░░] 50%`, and renders a directory table."

**Raw GenAI output:**

```python
def format_size(bytes_count: int) -> str:
    if bytes_count <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    digit_group = int(math.floor(math.log(bytes_count, 1024)))
    digit_group = min(digit_group, len(units) - 1)
    value = bytes_count / (1024 ** digit_group)
    return f"{int(value)} B" if digit_group == 0 else f"{value:.2f} {units[digit_group]}"


def render_progress_bar(filename, transferred, total,
                        speed_bytes_sec=0.0, width=30):
    percentage = min(100.0, (transferred / total) * 100.0)
    filled_length = int(round(width * transferred / float(total)))
    bar = "█" * filled_length + "░" * (width - filled_length)
    return f"File: {filename}\n[{bar}] {percentage:5.1f}%"
```

**Review and refinement:**

- The implementation handles `total <= 0` to prevent division by zero and
  caps the filled portion at the configured width.
- Tests cover byte-unit formatting, connection states, progress calculations,
  empty listings, and formatted directory entries.

## August 3, 2026 — Week 2 Filesystem, Concurrency, and Integration Contract

**Exact prompt:**
> "ok qua làm role C đi"

**English translation:**
> "Okay, move on to implementing Role C."

**Raw GenAI output:**

The generated implementation added `common/filesystem_service.py` with the
following main contract. The complete generated artifact remains in the source
file for line-by-line review.

```python
class FilesystemOperationError(Exception):
    def __init__(self, operation: str, reply_code: int, message: str) -> None:
        super().__init__(message)
        self.operation = operation
        self.reply_code = reply_code
        self.message = message


class TransferCancelledError(FilesystemOperationError):
    def __init__(self, operation: str = "transfer") -> None:
        super().__init__(operation, 426, "Transfer aborted.")


@dataclass(frozen=True)
class UploadResult:
    path: str
    bytes_written: int


class PathLockRegistry:
    """Provide per-path locks without serializing unrelated files."""


class FilesystemService:
    """Root-confined filesystem operations used by TCP and UDP modules."""

    def store(self, cwd, client_path, chunks, cancel_event=None):
        path = self.resolve(cwd, client_path)
        return self._atomic_upload(path, chunks, cancel_event, append=False)

    def append(self, cwd, client_path, chunks, cancel_event=None):
        path = self.resolve(cwd, client_path)
        return self._atomic_upload(path, chunks, cancel_event, append=True)
```

The output also changed `FTPServer.stop()` to snapshot active clients under the
registry lock, release that lock, clean up each client, and then join its thread.
New tests cover traversal, independent session paths, atomic upload, transfer
cancellation, concurrent append, unique STOU names, session reporting, and
shutdown while a client remains connected.

**Review and refinement:**

- **Role boundaries:** No Role A command parser or Role B RDT protocol was
  invented because those modules are not available on this branch. A documented
  integration contract was created instead.
- **Path safety:** An empty client path previously returned `cwd` without
  validating it. Validation was added, and `LIST`/`NLST` now hide symbolic links
  that resolve outside the FTP root.
- **File lifecycle:** `STOR` and `APPE` write to a hidden `.part` file, flush it
  with `os.fsync()`, and commit with `os.replace()` only after success. An error
  or cancellation removes the temporary file and preserves the old destination.
- **Concurrency:** Locks are scoped to resolved paths. Two clients cannot mix
  bytes while appending to one file, while unrelated files remain concurrent.
- **Deadlock fix:** The old shutdown path held `clients_lock` and then called
  `cleanup()`, which attempted to acquire the same lock through
  `unregister_client()`. Releasing the registry lock before cleanup removes this
  deadlock.
- **Log safety:** The first test run reported `88 passed, 1 skipped` plus a
  thread warning because a Windows terminal could not encode Vietnamese log
  text. A safe encoding fallback, timestamps, session IDs, and password
  redaction were added.
- **Final verification:** `py -m pytest -v` collected 90 tests and reported
  `89 passed, 1 skipped` with no warnings. The symlink test was skipped because
  the Windows environment did not permit symlink creation. The WSL suite was
  not run because that environment does not currently have `pytest` installed.
- **Document ownership:** `docs/report.md` was not modified. Role C notes are
  kept separately in `docs/role-c-week-2.md` for review before integration into
  the shared report.
