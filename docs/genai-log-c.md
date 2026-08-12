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

- `planning/reference/Project1_SocketProgramming_2026.md` §1.1–1.2 and §2.2–2.3
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

## August 9, 2026 — Final-week Go-Back-N Excellent RDT completion

**Exact prompt:**
> "Implement the plan." followed by the group decision: "ok chốt" for the
> simplest sliding-window mechanism, Go-Back-N with window 4.

**Raw GenAI output summary:**

The proposed implementation retained the public RDT header and adapter APIs,
added a `window_size` transfer-context setting, made `START` wait for a valid
ACK with a finite retry limit, and replaced the one-packet send loop with a
bounded Go-Back-N loop using cumulative ACKs and retransmission from the oldest
unacknowledged packet.

**Manual refinement:**

- Selected Go-Back-N instead of Selective Repeat because the existing receiver
  already commits only in-order packets; this avoids adding a reorder buffer.
- Fixed receiver behavior so repeated START receives an ACK, duplicate/future
  packets re-ACK the last contiguous sequence, and no duplicate payload is
  yielded.
- Added direct protocol tests proving four data packets are sent before the
  first cumulative ACK and that a lost START ACK causes retry before DATA.
- Added production FTP E2E coverage for STOU, APPE, HASH and TYPE; preserved
  existing ABOR/disconnect atomic-cleanup tests.
- Did not claim two-machine LAN success because that needs a physical second
  machine and saved artifacts.

**Affected files:**

- `common/rdt_context.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`
- `tests/test_rdt.py`, `tests/test_e2e_transfer.py`
- `docs/api-contract.md`, Role C status/history/evidence documents

**Verification:**

```text
python3 -m pytest tests/test_rdt.py -q                         -> 27 passed
python3 -m pytest tests/test_rdt_fault_injection.py tests/test_transfer_manager.py tests/test_e2e_transfer.py -q
                                                               -> 22 passed
python3 -m pytest tests/test_e2e_transfer.py -q                -> 6 passed
python3 -m pytest -q                                           -> 192 passed in 93.06s
```

## August 9, 2026 — Final Role A/C Compatibility Audit

**Exact prompt:**
> "Bạn kiểm tra role c và a lại nhé, xem ok chưa"

**Raw GenAI output summary:**

The audit checked that the Go-Back-N work did not change Role A command grammar,
reply ownership, `ClientHandler`, or the `TransferManager` adapter boundary. It
then ran separate Role A control/session tests and focused Role C filesystem,
RDT, CLI and FTP E2E tests.

**Evidence:** Role A `63 passed in 5.71s`; Role C `135 passed in 86.22s`.
The remaining unverified items are physical two-machine LAN evidence and formal
A/B release sign-off, not an automated A/C compatibility failure.

## August 9, 2026 — Windows ACTIVE demo CLI encoding repair

**Exact prompt:**
> The user pasted an ACTIVE-LAN traceback ending in `UnicodeEncodeError` from
> the Windows CP1252 console while rendering Unicode progress blocks.

**Manual refinement:**

- The RDT transfer was not changed: the failure was display-only after the TCP
  connection succeeded.
- Added a console-safe print boundary in `client/demo_transfer.py`; terminals
  that cannot encode `█`/`░` display replacement characters rather than crash.
- Added a CP1252 fallback test and retained the Unicode progress bar for UTF-8
  capable terminals.

**Verification:** `python3 -m pytest tests/test_cli_display.py
tests/test_e2e_transfer.py -q` — **13 passed in 23.09s**.

## August 9, 2026 — ACTIVE-LAN server-initiated UDP probe

**Exact prompt:**
> The user supplied a two-machine ACTIVE server log: STOR completed, but RETR
> retried RDT START ten times and ended with FTP `426` because no START ACK
> returned from the Windows client.

**Manual refinement:**

- The client had already created a stateful UDP path for ACTIVE upload; ACTIVE
  download had no client-to-server UDP packet before the server initiated START.
- Added a zero-payload START probe after the `150` RETR reply, using the same
  negotiated ACTIVE endpoint and transfer ID. It opens firewall/NAT state and
  carries no file data.
- Preserved the header, TCP command/reply flow and Go-Back-N sender behavior.

**Verification:** ACTIVE FTP E2E plus CLI tests: **8 passed in 5.42s**.

## August 9, 2026 — Two-machine ACTIVE/PASV evidence

**Exact prompt:**
> The user supplied real two-machine PASV and ACTIVE client success output,
> server lifecycle output, and source/server/client SHA-256 values.

**Evidence:** PASV and ACTIVE both completed upload plus download across server
`172.18.0.48` and client `172.18.0.49`. The 250.00 KB file has matching SHA-256
`b57b64b198d5d59ce5a22a9b9f25e72a7d081476d432051aa923f3dbebb90934`
at source, server and download. See `docs/evidence/final-lan-*-sha256.txt` and
the client logs. ACTIVE server-log/screenshot extraction remains a presentation
artifact, not a technical transfer blocker.

## August 9, 2026 — Final Role C regression and evidence refresh

**Exact prompt:**
> "ok tiep thoi, bay gio con phan gi nhi, de A va C cung lam"

**Raw GenAI output summary and manual refinement:**

- Re-ran the entire WSL2 suite after the console-safe output and ACTIVE UDP
  probe changes; the result is **199 passed in 96.72s**.
- Recorded the real two-machine PASV/ACTIVE result only where hashes/logs prove
  it. The ACTIVE server-log copy is treated as a presentation enhancement, not
  as a missing transfer implementation.
- Remaining A/C work is release hygiene and peer/report/oral sign-off; it is
  not an unresolved data-path defect.

**Affected files:** final-week verification evidence, project status, final
week plan, code-change history and this log.

**Verification:** `python3 -m pytest -q` — **199 passed in 96.72s**.

## August 9, 2026 — Role C Content Migration into Report Parts

**Exact prompt:**
> "à bạn giúp tôi viết các nội dung trong role-c-week-2 vào từng component trong folder report-parts, bao gồm những gì mà role c đã thực hiện trong final week ở phần planning vào trong đó sao cho đủ cái từng file bảo nha, sau đó xoá file role-c-week-2 plan"

**Raw GenAI output summary and manual refinement:**

- Mapped Role C implementation into technical components 01, 03, 06, 08 and 09;
  mapped test, contribution, limitation and provenance material into submission
  components 10–13.
- Used final evidence rather than stale Week 2 TODOs: 199 full tests, 6 expanded
  E2E tests, Go-Back-N verification and two-machine PASV/ACTIVE SHA-256.
- Kept `docs/report.md` untouched for Role B; removed the duplicated Role C
  Week 2 source only after its material had destinations in report-parts.

**Affected files:**

- `docs/report-parts/technical/01-introduction.md`, `03-system-architecture.md`,
  `06-filesystem-security.md`, `08-concurrency-integration.md`,
  `09-client-cli-logging.md`
- `docs/report-parts/submission/10-testing-results.md` through
  `13-genai-usage.md`, `docs/role-c-week-2.md`

**Verification:** Evidence links resolve to `docs/evidence/final-week-rdt-gbn-verification.md`
and final LAN artifacts; `git diff --check` and reference search are run at handoff.

## August 9, 2026 — Role-Week-2 Removal and Report-Link Repair

**Exact prompt:**
> "tôi quyết xoá week-2-role-a/b/c ròi, nên bạn format lại khúc đó giùm tôi. Cái technical 04 bạn sửa theo cái của C chứ ko theo commit, link nguồn gãy vì tôi xoá rồi nên bạn sửa nhé"

**Manual refinement:**

- Removed report-part links to deleted Role A/B/C Week 2 files and replaced
  them with the requirement checklist, API contract and final evidence.
- Documented `LIST`/`NLST` exactly as the shared contract states: textual TCP
  replies only, without UDP/RDT or `150`/`226` transfer lifecycle.
- Consolidated the contribution matrix so A, B and C each have one scope,
  evidence summary and one pending sign-off/percentage section.

**Verification:** Reference search and `git diff --check` are run after the
documentation cleanup.

## August 9, 2026 — Final-Week Plan Source Alignment

**Exact prompt:**
> "submission/14 chỉ giữ mapping/reference; không dùng draft lịch sử để claim trạng thái cuối.là sao nhỉ, và final-week plan cập nhật lại cho tôi nhé"

**Manual refinement:**

- Clarified in the plan that submission component 14 is a requirement-coverage
  cross-check, not the source of final Done/In progress claims.
- Redirected stale Role B/Role C Week 2 references to the surviving technical
  report parts, status, checklist and GenAI logs.
- Updated the proven C-F01 regression baseline to 199 tests while keeping B's
  wire-contract review and final A/B sign-off as pending work.

**Affected files:** `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md`,
`docs/code-change-history.md`, and this log.

**Verification:** Manual path/reference review and `git diff --check` passed.

## August 9, 2026 — Role B Release-State Reconciliation

**Exact prompt:**
> "PLEASE IMPLEMENT THIS PLAN: Đồng bộ và đóng các việc còn lại của Role B"

**Manual refinement:**

- Kept the evidence-backed RDT completion claim, but changed unrecorded A/C
  sign-off and contribution-percentage claims to pending release gates.
- Added a 20-question oral pack with real code/evidence locators directly to
  B-F03; the actual dry-run record must still be created only after the session.
- Made the project status and acceptance checklist the only locations that can
  close report, peer-evaluation, oral and Git release work.

**Affected files:** final-week plan, `docs/report.md`, requirement checklist,
project status, submission contribution component, code-change history and this log.

**Verification:** Static review against `docs/evidence/final-week-rdt-gbn-verification.md`;
`git diff --check` run after all documentation edits.

## August 9, 2026 — A/C Technical Audit and Evidence-Only Release Review

**Exact prompt:**
> "Review/sign-off chính thức phần TCP/command trong report ... C review/sign-off filesystem, concurrency, LAN/evidence trong report và các lỗi tài liệu"

**Manual refinement:**

- Recorded “technical audit passed” for A TCP/command and C
  filesystem/concurrency/LAN scopes, explicitly distinguishing it from personal
  signatures and the later team release decision.
- Verified existing LAN logs provide client IP, commands, active-session
  snapshots, transfer results and replies, so no new screenshot or dry-run
  evidence is required.
- Removed stale B wire-review/report-assembly claims, mapped Role B GenAI
  provenance into submission component 13, and removed blank log templates.

**Affected files:** report, report-parts, API contract, GenAI logs, status,
checklist, final-week plan, code-change history and this log.

**Verification:** `docs/evidence/final-lan-server.log`, final LAN client/hash
artifacts and `docs/evidence/final-week-rdt-gbn-verification.md` (45 RDT/fault
tests; 199 full tests); documentation consistency and `git diff --check` follow.

## August 9, 2026 — Screenshot Evidence Removal

**Exact prompt:**
> "tôi không cần screenshot nữa nên xoá file đó nha"

**Manual refinement:**

- Removed the eight screenshot files under `docs/evidence/screenshots/` after
  confirming their exact paths.
- Replaced active submission references with curated LAN server/client logs and
  SHA-256 files; historical notes now state that screenshots were removed from
  the submission evidence pack.

**Verification:** `final-lan-server.log` includes client IP, commands,
active-session snapshots, replies and transfer outcomes; PASV/ACTIVE client logs
and SHA-256 files remain available.

## August 9, 2026 — Requirement Reference Repair

**Exact prompt:**
> "bạn sửa cái lỗi tài liệu cho tôi nhé"

**Manual refinement:**

- Repaired active documentation links after the planning folder moved the
  immutable requirement into `planning/reference/`.
- Corrected submission component 14 to state that B-F01 wire-contract review
  is complete, rather than leaving a stale pending-review claim.

**Verification:** Repository-wide reference search resolves the current
requirement path; final-week plan records B-F01 as complete.

## August 9, 2026 — Screenshot Evidence Restore

**Exact prompt:**
> "ê chết, bạn revert các screenshot lại giùm tôi"

**Manual refinement:**

- Restored all eight tracked screenshot files from the current Git revision.
- Retained the documentation policy that logs and hashes are sufficient
  technical evidence; screenshots are now available again as supplementary
  presentation evidence.

**Verification:** `docs/evidence/screenshots/` contains the eight restored PNG
files.

## August 9, 2026 — Full TCP/UDP Sequence Diagram

**Exact prompt:**
> "bạn thêm cho tôi nhé"

**Manual refinement:**

- Added a Mermaid sequence diagram to report §2.4.1 with TCP authentication,
  PASV/PORT alternatives, `150 → 226/426`, RDT START/ACK, four-packet
  Go-Back-N DATA/ACK, FIN/ACK and ABORT/error flow.
- Kept filesystem writes and downloads distinct so the diagram shows ownership
  across A/B/C without claiming a separate TCP data connection.

**Verification:** Static review against `docs/api-contract.md` and
`docs/evidence/final-week-rdt-gbn-verification.md`.

## August 9, 2026 — Screenshot Capture Guide

**Exact prompt:**
> "bạn tạo 1 file md cho tôi, HD chạy và đặt tên ảnh ntn nhé và bổ sung mấy cái còn thiếu"

**Manual refinement:**

- Audited the restored PNG files against §2.4.7/§4.5 and visual content.
- Kept the usable PASV client and ACTIVE hash images; marked the old 186-test
  image and server image containing a startup error as unsuitable for final
  embedding.
- Added exact commands and filenames for four clean final screenshots.

**Verification:** Guide references real README commands, E2E test locator,
existing LAN logs and SHA-256 artifacts.

## August 10, 2026 — Final Shared-Filesystem and Release Evidence Pass

**Exact prompt:**
> "Implement the plan."

**Raw GenAI output summary:**
AI traced the lost-update risk to one `FilesystemService` and one lock registry
being created per client. It proposed server ownership of a shared service,
production-path concurrency tests, active-session log ordering, clean import
checks and final evidence synchronization.

**Manual refinement:**

- Made `FTPServer` create one filesystem service after creating the FTP root;
  each client borrows it through its `TransferManager`.
- Added both identity and real two-client same-file APPE tests. The final file
  must contain both complete payloads in either serialized order.
- Moved the connected/session snapshot after `handler.start()` and verified
  live sessions report `alive=True`.
- Preserved the RDT binary layout and corrected only the report/API field order
  and flag values. Embedded existing LAN logs, hashes and clean screenshots in
  report §7.

**Affected files:** threaded server/client integration, filesystem concurrency
tests, final report/evidence, API contract, status/checklist and planning.

**Verification:** focused A/C suite **71 passed + 28 subtests**; same-file APPE
**1 passed in 3.96s**; import smoke **1 passed**; full WSL2 suite **212 passed +
28 subtests in 97.52s**. Evidence:
`docs/evidence/final-code-fix-verification.md`.

## August 10, 2026 — MODE B/C Integration Review and Final Checklist

**Exact prompt:**
> "cái mode b/c sửa lại luôn đc không và bạn format lại final-code-fix-a-c thành các checklist cho dễ tick nha"

**Raw GenAI output summary:**
AI identified MODE as per-session TCP control state and proposed a production
E2E transfer proving that accepting B/C does not break the shared RDT path.

**Manual refinement:**

- Reviewed the Role A MODE change against C's transfer boundary: no RDT header,
  endpoint ownership, filesystem, atomic-write or cleanup rule changed.
- Added E2E upload after MODE B and download after MODE C with SHA-256 equality.
- Converted the A/C final code-fix document into task checklists and a DoD; Git
  clean-after-commit remains unticked because this working tree is not committed.

**Affected files:** E2E integration test, contract/report/status/evidence and
`planning/weekly-plans/final-code-fix-a-c.md`.

**Verification:** focused MODE/E2E run **61 passed + 28 subtests in 31.91s**;
full WSL2 regression **213 passed + 28 subtests in 108.71s**. Evidence:
`docs/evidence/final-code-fix-verification.md`.

## August 10, 2026 — Revert Role A Implementation for Owner Handoff

**Exact prompt:**
> "cả 2 cái nha, coi như chỉ giao task và cho a làm"

**Raw GenAI output summary:**
AI separated the final A/C diff by module ownership and proposed reverting only
Role A production code/tests while retaining Role C filesystem, concurrency and
integration changes.

**Manual refinement:**

- Restored Role A's TCP client, command handler, command tests and legacy
  client/server modules to their pre-final-fix Git state.
- Removed AI-added Role A framing/import/MODE tests and the MODE B/C E2E case.
- Kept C's shared `FilesystemService`, active-session ordering, same-file APPE
  regression and RDT integration unchanged.
- Converted the final-code-fix document to a Role C-only checklist; A tasks are
  pending owner implementation and fresh evidence.

**Verification:** Role C focused suite **24 passed in 33.80s**; current full
WSL2 regression **205 passed in 103.08s**.

## August 10, 2026 — Role A Production Audit Fix

**Exact prompt:**
> "Implement the plan."

This referred to the accepted plan titled “Review và sửa production path của
Role A”, produced after the full Role A review request in the same conversation.

**Raw GenAI output summary:**
The audit proposed fixing MODE/TYPE state mismatch, extending START metadata
without changing the 20-byte header, making client downloads atomic, buffering
TCP replies, completing strict auth/STAT/HELP/STOU behavior, removing broken
legacy modules, adding negative production tests, and assigning screenshots to
Role A.

**Manual refinement:**

- Reproduced silent corruption through the real TCP → session → RDT → Block
  decoder → filesystem path before changing code.
- Preserved existing Role C/oral worktree changes outside the review commit.
- Added MODE and TYPE only to the START payload; header layout, flags, checksum,
  retry and Go-Back-N window remain unchanged.
- Kept filesystem ownership intact and used a separate atomic client-download
  helper rather than moving server path decisions into Role A code.
- Recorded a randomized fault-test retry-limit failure and its successful rerun
  instead of hiding the flaky run.

**Affected files:** production client/control/RDT/codec/transfer modules, their
tests, API contract, status/checklist/report, final plan and review evidence.

**Verification:** targeted **140 passed + 338 subtests**; E2E **14 passed + 8
subtests**; fault injection **19 passed + 11 subtests**; final full regression
**271 passed + 357 subtests in 192.88s**.

## August 10, 2026 — Role C Oral Guide Audit and Generation

**Exact prompt:**
> "Và các phần nào chưa thêm vào thì bạn để trống oral nhé, tôi thêm sau"

The attached prompt was the full `TCREI Prompt — Tạo tài liệu Oral cho Role C`,
requiring rubric mapping, architecture/execution flow, Role C code explanation,
dependency/what-if analysis, tests/evidence, five levels of oral questions,
teacher traps, rapid review and a final checklist.

**Raw GenAI output summary:**
AI audited the official rubric, current source, tests, API/status/report parts
and Role C evidence, then generated a Vietnamese 20-section Word oral guide.
It proposed leaving explicit blanks for features without current implementation
or evidence instead of filling them from stale planning claims.

**Manual refinement:**

- Prioritized official requirement → current code → tests/evidence → docs →
  planning and recorded current inconsistencies explicitly.
- Left `MODE B/C`, `STAT <path>`, buffered TCP reply framing, final contribution
  percentage and release hash/sign-off as `________` where an implementation
  answer would be unverifiable.
- Added exact Role C caller/callee, input/output, state, error and removal-impact
  explanations for path validation, per-path locks, atomic upload, threaded
  server/client lifecycle and transfer orchestration.
- Rendered through Microsoft Word because LibreOffice was unavailable. The
  first render exposed alternating headers and split rows/paragraphs; the
  builder was corrected and all 19 final pages were inspected again.

**Affected files:** `docs/Role-C-Oral-Guide.docx`,
`docs/build_role_c_oral.py`, Role C weekly/evidence/status/history documents.

**Verification:**

- `wsl python3 -m pytest tests/test_filesystem_service.py
  tests/test_transfer_manager.py tests/test_threaded_server.py
  tests/test_e2e_transfer.py -q` — **24 passed in 31.37s**.
- Microsoft Word PDF export + PyMuPDF PNG render — **19/19 pages inspected**;
  no clipping, overlap or split table rows in the final build.

## August 11, 2026 — Interactive Terminal Client

**Exact prompt:**
> "tôi muốn vậy á, tôi phải thực hiện command từ terminal"

**Raw GenAI output summary:**
AI identified that `nc` can send TCP control text but cannot create the
project's UDP/RDT data channel. It proposed a small `python3 -m client.ftp_cli`
entry point: preserve raw control commands and dispatch file commands to the
existing `FTPClient` production methods.

**Manual refinement:**

- Kept the shared TCP/UDP/RDT contract unchanged; the CLI is only an adapter.
- Used `shlex` so quoted local file paths work, and rejected missing local
  upload files before initiating a server transfer.
- Preserved FTP wire syntax at the server boundary while documenting the CLI
  convenience syntax `STOR <local-file> [remote-file]` and `APPE <local-file>
  [remote-file]`.
- Added a focused dispatch test, then ran the existing E2E suite that exercises
  the exact production transfer methods called by the CLI.

**Affected files:** `client/ftp_cli.py`, `tests/test_ftp_cli.py`, `README.md`,
`docs/project-status.md`, and `docs/code-change-history.md`.

**Verification:** `python3 -m pytest tests/test_ftp_cli.py
tests/test_ftp_client.py -v` — **7 passed in 0.60s**; `python3 -m pytest
tests/test_e2e_transfer.py -v` — **14 passed + 8 subtests in 83.16s**.

## August 11, 2026 — Interactive Demo Login

**Exact prompt:**
> "mỗi làn làm là mỗi lần reset ah"

**Raw GenAI output summary:**
AI explained that real authentication needs a server-side source of truth. The
user chose a demo-only policy instead: accept any non-empty username/password
entered by the client.

**Manual refinement:**

- Removed production default credentials and the unused server-side credential
  plumbing.
- Kept interactive CLI login as explicit `USER`/`PASS` lines, matching the
  required FTP command surface and avoiding hidden `getpass` input.
- Kept empty-password rejection and client retry behavior in the terminal UI.
- Updated command tests to cover the agreed non-empty credential policy.

**Affected files:** server startup/handler modules, client login/CLI/demo,
authentication/E2E tests, README, project status and code history.

**Verification:** `python3 -m pytest tests/test_ftp_cli.py
tests/test_ftp_client.py tests/test_commands.py -q` — **66 passed in 0.97s**;
`python3 -m pytest tests/test_e2e_transfer.py -v` — **14 passed + 8 subtests
in 83.99s**.

**Final regression:** `python3 -m pytest -q` — **274 passed, 357 subtests
passed in 186.46s**.

## August 12, 2026 — CLI `150` Reply Display and Evidence Refresh

**Exact prompt:**
> "ko thể chạy ra 150 mà phải sửa lại hả" and "ok v đi"

**Raw GenAI output summary:**

The review found that the server already sent `150`, but `FTPClient` consumed
it internally to obtain `transfer_id`; the interactive CLI printed only its
final `226` summary. The proposed minimal change was an optional callback for
the received initial reply, called only by the terminal adapter.

**Manual refinement:**

- Kept the TCP `150 → 226` lifecycle, UDP/RDT path and server code unchanged.
- Passed `print` only from `ftp_cli` to the existing upload/download methods;
  no new dependency, protocol field or CLI option was added.
- Added one focused assertion that transfer commands expose both initial replies
  through the callback, then captured a real localhost PASV upload/download.

**Affected files:** `.gitignore`, `client/ftp_client.py`, `client/ftp_cli.py`,
`tests/test_ftp_cli.py`, `README.md`, report/client-logging/status/history
documents, and `docs/evidence/cli-transfer-replies-150-226*`.

**Verification:** `python3 -m pytest tests/test_ftp_cli.py
tests/test_ftp_client.py -v` — **7 passed in 1.86s**. A localhost PASV CLI run
showed `150` before both `STOR` and `RETR`, `226` after each transfer, and
identical SHA-256 values for source, server upload and client download.

## August 12, 2026 — Documentation Source of Truth

**Exact prompt:**
> "bạn thêm cho tôi đi, sau khi đọc các folder trong mục docs. Trước khi làm cái đó, pull code về, review lại, bỏ các artifact bi dư, thêm file md source of truth roi push lên github lại"

**Raw GenAI output summary:**

The review found that the project already had separate authoritative files for
requirements, API ownership, current status, acceptance evidence, and report
narrative, but no concise index explaining their precedence. It also found a
duplicate A/C report whose content had been moved to planning, a duplicate
screenshot index represented in `report.md`, and ignored runtime output.

**Manual refinement:**

- Kept the new document as a short routing page rather than copying technical
  details that would drift.
- Kept tracked FTP fixtures and curated evidence; removed only the confirmed
  duplicate documents and ignored runtime artifacts.
- Made `project-status.md` link to the index without changing any acceptance
  claim, API, or protocol behavior.

**Affected files:** `docs/source-of-truth.md`, `docs/project-status.md`,
`docs/code-change-history.md`, `docs/genai-log-a.md`, `docs/genai-log-c.md`; moved
`docs/report-fix-a-c.md` and removed ignored runtime artifacts.

**Verification:** `git pull --rebase` reported the branch up to date; all
Markdown headings under `docs/` were reviewed; `git diff --check` passed.

## August 12, 2026 — Final PDF and Screenshot Compatibility

**Exact prompt:**
> "bạn sửa cái đó + source of truth lại nhá, tôi ms thêm cái file pdf final của team á"

**Raw GenAI output summary:**

The newly added `docs/Hybrid_FTP_Technical_Report.pdf` is the final team
submission artifact. The prior removal of `docs/screenshots.md` can cause a
delete/modify conflict for teammates with older branches.

**Manual refinement:**

- Restored `screenshots.md` as a short compatibility index, without duplicating
  the full report captions.
- Linked the final PDF from `source-of-truth.md` while retaining code/tests and
  `project-status.md` as authorities for current technical behavior and status.

**Affected files:** `docs/Hybrid_FTP_Technical_Report.pdf`,
`docs/screenshots.md`, `docs/source-of-truth.md`,
`docs/code-change-history.md`, and `docs/genai-log-c.md`.

**Verification:** confirmed the PDF and every indexed screenshot file exists.

## August 12, 2026 — README Documentation Links

**Exact prompt:**
> "bạn nhớ cập nhật readme nx nhé"

**Raw GenAI output summary:**

The README already had a documentation section, so the minimal change was to
link the source-of-truth page and final PDF there.

**Manual refinement:**

- Added the two links in both the directory map and documentation rules.
- Did not duplicate the source-of-truth ordering in README.

**Affected files:** `README.md`, `docs/code-change-history.md`, and
`docs/genai-log-c.md`.

**Verification:** `git diff --check` passed; both linked files exist.
