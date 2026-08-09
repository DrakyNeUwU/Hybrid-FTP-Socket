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

## August 8, 2026 — Week 2.5 Integration Review and Evidence Update

**Exact prompt:**
> "bạn thêm lịch sử genai-log-c của tôi nhé, và cập nhật tuần 2.5-fix, review lại tuần này coi còn gì không"

**English translation:**
> "Please add my history to genai-log-c, update week 2.5-fix, and review this
> week to see what is still missing."

**Raw GenAI output:**

The review identified that Role C's filesystem work was largely implemented,
but the shared A–B–C integration gates were still open. It also identified a
contract mismatch between `TransferManager` and the RDT adapters, which had to
be recorded as an integration issue rather than claimed as complete.

**Review and refinement:**

- Role C ownership remains the filesystem boundary: atomic `.part` handling,
  root confinement, path locks, unique STOU names, and cleanup.
- `docs/api-contract.md` remains the source of truth; Role C does not redefine
  the RDT wire format or FTP command grammar.
- The status was updated to distinguish unit/fault-test evidence from missing
  FTP server Active/PASV evidence.
- Remaining Role C evidence is explicitly listed: symlink/path-security test,
  multi-client test, concurrent append, server shutdown, and source/destination
  SHA-256 comparison through the real FTP workflow.

**Evidence recorded:**

- `docs/project-status.md`
- `docs/code-change-history.md`
- `planning/weekly-plans/tuan-2.5-fix.md`
- Existing Role C implementation and tests in `common/`, `server/`, and `tests/`

## August 8, 2026 — Manual Active Transfer Demo Evidence

**Exact prompt:**
> "PS C:\\Code\\Code\\socket> python -m client.demo_transfer .\\demo.bin --remote demo-active.bin --mode ACTIVE ... Success: ACTIVE upload + download for demo-active.bin Vậy là xog r hả"

**English translation:**
> "The Active demo returned success for upload and download. Is it finished?"

**Raw GenAI output:**

The response confirmed that Active transfer completed and asked for PASV plus
SHA-256 checks before claiming the full weekly demo was complete.

**Review and refinement:**

- Recorded the manual Active result as demo evidence, not as proof that every
  integration exit gate is complete.
- Kept manual PASV demo, multi-client, ABOR/disconnect, and cross-machine
  testing explicitly pending.
- Updated the Week 2 Role C evidence in the same format as the report parts:
  requirement/evidence, implementation boundary, limitations, and next work.

## August 8, 2026 — Manual PASV Transfer Confirmation

**Exact prompt:**
> "1. PASV demo đã ok , mấy phần kia phần nào làm 1 mình tôi đc nhỉ"

**English translation:**
> "The PASV demo is okay. Which remaining parts can I do on my own?"

**Evidence update:**

The user confirmed the localhost PASV manual demo passed. The checklist/status
now treats manual Active and PASV as complete, while retaining the need to save
the terminal output, screenshots, and SHA-256 values for final submission.

## August 8, 2026 — WSL2 Full Test Repair and Verification

**Exact prompt:**
> The user pasted a WSL2 `pytest -v` result showing 183 passed and three
> failures: one `ClientHandler` socket-address failure and two stale ECHO-based
> threaded-server tests.

**Raw GenAI output:**

The diagnosis separated one production robustness bug from two obsolete tests.
The fix made `ClientHandler` tolerate a non-IP `socketpair()` address and
replaced debug ECHO expectations with the real FTP `NOOP` command.

**Review and refinement:**

- The server did not regain debug commands; tests were corrected to preserve the
  project command specification.
- The socket fallback only affects test/non-IP sockets and preserves normal TCP
  server IP discovery.
- WSL2 verification after the fix: `python3 -m pytest -q` reported
  **186 passed in 104.09s**. The saved log is
  `docs/evidence/week-2.5-pytest.log`.

## August 8, 2026 — Saved Active/PASV Hash Evidence

**Exact prompt:**
> "ok chạy xog r a"

**Raw GenAI output:**

The evidence folder was inspected. Both Active and PASV SHA-256 files contain
matching source, server, and downloaded-client hashes. The saved pytest log
contains only progress output, so it is not treated as a complete terminal
artifact until it includes the final pass summary.

**Evidence:**

- `docs/evidence/week-2.5-active-sha256.txt`
- `docs/evidence/week-2.5-pasv-sha256.txt`

## August 8, 2026 — Three Concurrent PASV Clients

**Exact prompt:**
> "nói chung bây giờ , mình cần làm những task còn lại của role c" followed by
> "ok" to begin the multi-client task.

**Raw GenAI output:**

The proposed next Role C task was an automated three-client transfer test. The
first version of the client reused one repository download directory, so the
review added an optional `download_dir` argument and assigned each test client
a separate temporary directory.

**Review and refinement:**

- The test uses three real TCP sessions, synchronizes them before transfer, and
  runs PASV upload then download in parallel.
- It asserts the server has four live control clients before release (three
  workers plus the fixture client), waits for all workers with a finite timeout,
  and compares SHA-256 at source, FTP root, and each download directory.
- This is evidence for independent concurrent transfers; it does not claim to
  prove ABOR/disconnect cleanup or cross-machine networking.

**Affected files:**

- `client/ftp_client.py`
- `tests/test_e2e_transfer.py`
- `docs/evidence/week-2.5-three-client.log`
- `docs/role-c-week-2.md`, `docs/project-status.md`,
  `docs/code-change-history.md`, `planning/weekly-plans/tuan-2.5-fix.md`

**Verification:**

```text
python3 -m pytest tests/test_e2e_transfer.py::TestEndToEndPasvTransfer::test_three_pasv_clients_transfer_independently -v
1 passed in 5.34s
```

The wider end-to-end regression was also run and saved in
`docs/evidence/week-2.5-e2e-transfer.log`:

```text
python3 -m pytest tests/test_e2e_transfer.py -v
3 passed in 15.47s
```

## August 8, 2026 — ABOR and Disconnect During a Waiting Upload

**Exact prompt:**
> "ok làm tiếp thoi, cái nào cần tôi thủ công thì bảo nhé"

**Raw GenAI output:**

The review found that RDT cancellation/timeout raises `RuntimeError`, while
`TransferManager` only converted `OSError`, `TypeError`, and `ValueError` into
an FTP result. The change added `RuntimeError` to the same failure mapping so
the command worker returns a structured `426` instead of relying on its generic
exception fallback.

**Review and refinement:**

- Added a production PASV `STOR` test that sends no UDP data, waits until a
  `.part` file exists, then issues `ABOR` through the real TCP control socket.
- Added the same waiting-upload setup but closes the control socket instead.
- Both tests assert temporary-file removal and preservation of the existing
  target; the disconnect test also waits for the server active-client count to
  return to the fixture's one remaining client.
- No manual step is required for this result because automated tests exercise
  the actual TCP command, UDP wait, RDT adapter, transfer manager, and
  filesystem cleanup path.

**Affected files:**

- `server/transfer_manager.py`
- `tests/test_e2e_transfer.py`
- `docs/api-contract.md`, `docs/role-c-week-2.md`, `docs/project-status.md`,
  `docs/code-change-history.md`, `planning/weekly-plans/tuan-2.5-fix.md`

**Verification:**

```text
python3 -m pytest tests/test_e2e_transfer.py -v
5 passed in 18.03s

python3 -m pytest -q
189 passed in 113.94s
```

Logs: `docs/evidence/week-2.5-e2e-transfer.log` and
`docs/evidence/week-2.5-pytest.log`.

## August 8, 2026 — LAN Demo Launcher

**Exact prompt:**
> "vậy làm tiếp thôi"

**Raw GenAI output:**

The remaining evidence requires two physical machines, so the server entry
point was made configurable instead of hard-coding localhost. PASV needs a
separate advertised IP when the TCP listener binds `0.0.0.0`; otherwise a
remote client may receive an unusable endpoint.

**Review and refinement:**

- Added backward-compatible `FTPServer.advertised_host` and command-line
  `--host`, `--port`, `--ftp-root`, `--advertise-host` arguments.
- `ClientHandler` uses the configured advertised host only when supplied;
  localhost tests keep the previous socket-derived address.
- This prepares a LAN demo but cannot prove two-machine routing in one local
  WSL2 environment; that final run is explicitly manual evidence.

**Affected files:**

- `server/threaded_server.py`
- `server/client_handler.py`
- `README.md`
- `docs/api-contract.md`, `docs/project-status.md`,
  `docs/code-change-history.md`, `planning/weekly-plans/tuan-2.5-fix.md`

**Verification:**

```text
python3 -m server.threaded_server --help
python3 -m pytest tests/test_threaded_server.py tests/test_e2e_transfer.py -q
10 passed in 21.56s
```

## August 8, 2026 — Week 2.5 Checklist Consolidation

**Exact prompt:**
> "cái tuan-2.5-fix đang bị nhiều cái checklist, lằng quằng nhiều cái quá,
> format lại là checklist của role a, b ,c thôi, dependency, definition of
> done. Reeview tổng"

**Raw GenAI output:**

The old file contained several historical phases and audits beside current
tasks, leaving completed and obsolete items mixed with pending work. It was
replaced with one current checklist grouped by Role A, Role B, Role C,
dependencies, and Definition of Done.

**Review and refinement:**

- Completion claims are linked to concrete evidence: full WSL2 pytest (189
  passed), E2E (5 passed), hash files, and concurrent-client log.
- Only three unresolved categories remain: shared `LIST/NLST` design,
  two-machine LAN evidence, and unified progress/logging.
- Historical detail was preserved in `docs/code-change-history.md`, rather
  than duplicated in the operational checklist.

**Affected files:**

- `planning/weekly-plans/tuan-2.5-fix.md`
- `docs/code-change-history.md`
- `docs/genai-log-c.md`

## August 8, 2026 — LIST/NLST Transport Clarification

**Exact prompt:**
> "cái quyết định chung list/nlst đó là sao" and "trong file requirement như
> thế nào nhỉ" followed by "v đi"

**Raw GenAI output:**

The requirement was read directly. It states that every approved command and
every reply use the TCP control channel, while UDP carries actual file payload.
LIST/NLST return directory metadata, so their current TCP textual result is
aligned with the requirement and does not need an RDT transfer.

**Manual refinement:**

- Recorded the decision in `docs/api-contract.md` §6.1.
- Removed LIST/NLST from the remaining dependency and Definition of Done items.
- Kept Role A as command/reply owner and Role C as validated listing provider.

**Evidence:**

- `planning/Project1_SocketProgramming_2026.md` §1.1–1.2 and §2.2–2.3
- Full WSL2 pytest: 189 passed in 113.94s

## August 8, 2026 — Real CLI Progress and Server Lifecycle Logging

**Exact prompt:**
> "à vậy phần nào role C, cứ làm tiếp đi"

**Raw GenAI output:**

The review found that progress rendering existed only as a UI helper and server
logging did not yet show all information needed for the demo checklist. The
implementation normalized the core RDT callback, connected it to `FTPClient`
and `demo_transfer`, and added thread-safe lifecycle logs.

**Manual refinement:**

- PASS arguments are redacted before logging.
- Server logs connection IP, command, reply, session ID, transfer ID, active
  session snapshot, transfer mode, byte count and result.
- A mock-server cleanup regression was found during full pytest and fixed by
  treating active-session APIs as optional for minimal test doubles.

**Affected files:**

- `server/logging_utils.py`, `server/threaded_server.py`,
  `server/client_handler.py`, `server/command_handler.py`
- `common/rdt_receiver.py`, `client/ftp_client.py`,
  `client/demo_transfer.py`, `tests/test_e2e_transfer.py`

**Verification:**

```text
Focused command/server/E2E/CLI tests: 62 passed in 22.16s
Full WSL2 pytest: 189 passed in 102.50s
```

Evidence: `docs/evidence/week-2.5-cli-logging.log` and
`docs/evidence/week-2.5-pytest.log`.

## August 8, 2026 — Correct Download Progress Total

**Exact prompt:**
> The user pasted the manual PASV progress/server logs. Upload rose normally,
> but every download chunk displayed 100%.

**Raw GenAI output:**

The server RDT sender did not receive the validated file size for RETR, so it
sent zero in the RDT START metadata. The receiver therefore had no total and
the CLI used the current chunk count as a fallback total.

**Manual refinement:**

- Added optional `total_bytes` to the shared `TransferContext`.
- `TransferManager.download()` obtains the validated size from
  `FilesystemService`; `RDTSenderAdapter` passes it to RDT START.
- Added an E2E assertion requiring every download progress callback to report
  the source file's actual size.

**Verification:**

```text
E2E: 5 passed in 17.61s
Full WSL2 pytest: 189 passed in 106.91s
```

The old manual progress log remains valid for successful PASV transfer and hash,
but a new screenshot is needed to show the corrected download display.

## August 8, 2026 — PASV Progress Screenshot Evidence

**Exact prompt:**
> "ok xog r á, đã lưu"

**Evidence update:**

The user confirmed that the corrected PASV server-log, progress, and success
screenshots were saved under `docs/evidence/screenshots/`. This closes the
localhost visual-evidence item. LAN remains pending because it requires a
second machine/network path.

## August 9, 2026 — Final-Week Source-of-Truth Consolidation

**Exact prompt:**
> "Nhìn theo góc Product Manager... từ cái này, bạn lên plan sửa cho tôi nhé"
> followed by "Implement the plan."

**Raw GenAI output summary:**

The review found that the repository had accurate evidence but conflicting
current-status language: the report and report parts still contained
placeholders, the Role B Week 2 snapshot said pytest had not run, and the
requirement checklist had been deleted. It proposed one operational status,
one acceptance checklist, a short final-week dashboard, and a final report
that makes only evidence-backed claims.

**Manual refinement:**

- Recreated `docs/requirement-checklist.md` as the pre-submission acceptance
  gate and made `docs/project-status.md` the only current-status source.
- Kept `docs/report.md` unchanged because Role B owns its final-week completion;
  the checklist/status make that ownership and its A/C technical sign-off gate
  explicit.
- Added a compact dashboard to the final-week plan and historical banners to
  week reports and `docs/report-parts/`, preventing stale snapshots from being
  presented as the current project state.

**Affected files:**

- `docs/project-status.md`, `docs/requirement-checklist.md`
- `docs/report-parts/README.md`, `docs/report-parts/submission/14-requirement-compliance.md`
- `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md` and historical week documents
- `docs/code-change-history.md`

**Verification:**

- Existing evidence referenced without changing its claims: WSL2 full pytest
  **189 passed in 106.91s** and FTP E2E **5 passed in 18.03s**.
- Repository search and Git status are run after the document change to verify
  current documents do not retain stale completion claims and the recreated
  checklist is tracked as an intentional change.

## August 9, 2026 — Planning and Report-Part Folder Structure

**Exact prompt:**
> "bạn format lại cái filephanchia cv theo format Đổi filephanchiacv/ thành cấu trúc dễ hiểu: planning/ ├── status/ ├── weekly-plans/ đi"
> followed by "tượng tự với reportpart, bạn format lại cho đẹp nhé"

**Raw GenAI output summary:**

The restructuring separated immutable requirements and ownership from weekly
planning, kept one status source instead of copying status files, and grouped
report drafts by technical content versus submission material.

**Manual refinement:**

- Renamed `filephanchiacv/` to `planning/`; requirement and role ownership are
  at its root, week documents are in `planning/weekly-plans/`, and
  `planning/status/README.md` routes users to `docs/project-status.md`.
- Grouped report drafts under `docs/report-parts/technical/` (01–09) and
  `docs/report-parts/submission/` (10–14), with a root README for structure,
  ownership and merge rules.
- Updated internal references without changing `docs/report.md`, which remains
  Role B's final-week responsibility.

**Affected files:**

- `planning/`, `docs/report-parts/`, and their internal references
- `docs/api-contract.md`, `docs/project-status.md`,
  `docs/requirement-checklist.md`, `docs/report_role_a_week2.md`, `.gitignore`,
  `README.md`

**Verification:**

- Repository search confirms no operational `filephanchiacv/` reference remains;
  the exact user prompt above intentionally retains the historical folder name.
- `git diff --check` is run after the moves and link updates.
