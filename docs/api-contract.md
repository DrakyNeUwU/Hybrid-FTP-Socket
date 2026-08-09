# Shared API Contract — Hybrid FTP

**Nguồn chuẩn duy nhất cho A–B–C:** tài liệu này.  
**Trạng thái:** contract được chốt ở mức tài liệu; phần ghi `Proposed` hoặc
`Needs change` chưa được xem là đã triển khai.  
**Nguồn requirement:** `docs/requirement-checklist.md` và
`planning/Project1_SocketProgramming_2026.md`.

## 1. Ownership và nguyên tắc

| Role | Owner chính | Không tự ý làm thay |
|---|---|---|
| A | TCP control, parser, FTP replies, session, transfer command orchestration | Không tự resolve/write client path, không tự định nghĩa RDT packet |
| B | UDP endpoint use, RDT packet, ACK, sequence, retry, FIN/ABORT | Không tự quyết định FTP reply hoặc filesystem commit |
| C | FTP-root filesystem, atomic file lifecycle, locks, threaded server, CLI/logging, integration | Không tự đổi command grammar/RDT format |

Mọi thay đổi API/header/reply/cleanup phải được A, B, C review và cập nhật trong
file này trước khi sửa report hoặc code.

## 2. API Role A → Role C: filesystem

**Module/class hiện có:** `common.filesystem_service.FilesystemService`.  
**Resource owner:** C owns the service and all resolved paths/file handles;
A owns only session command state.  **Status:** `Existing` for listed methods;
`Needs change` where integration has not been wired.

```python
class FilesystemService:
    def resolve(self, cwd: str, client_path: str = "") -> str: ...
    def display_path(self, path: str) -> str: ...
    def change_directory(self, cwd: str, client_path: str) -> str: ...
    def parent_directory(self, cwd: str) -> str: ...
    def list(self, cwd: str, client_path: str = "") -> list[dict]: ...
    def names(self, cwd: str, client_path: str = "") -> list[str]: ...
    def stat(self, cwd: str, client_path: str) -> dict: ...
    def size(self, cwd: str, client_path: str) -> int: ...
    def modified_time(self, cwd: str, client_path: str) -> str: ...
    def hash(self, cwd: str, client_path: str,
             algorithm: str = "sha256") -> str: ...
    def make_directory(self, cwd: str, client_path: str) -> str: ...
    def remove_directory(self, cwd: str, client_path: str) -> None: ...
    def delete(self, cwd: str, client_path: str) -> None: ...
    def rename(self, cwd: str, old_path: str, new_path: str) -> None: ...
    def prepare_retrieve(self, cwd: str, client_path: str) -> str: ...
    def read_chunks(self, cwd: str, client_path: str,
                    chunk_size: int = 1024) -> Iterator[bytes]: ...
    def store(self, cwd: str, client_path: str, chunks: Iterable[bytes],
              cancel_event: threading.Event | None = None) -> UploadResult: ...
    def append(self, cwd: str, client_path: str, chunks: Iterable[bytes],
               cancel_event: threading.Event | None = None) -> UploadResult: ...
    def store_unique(self, cwd: str, chunks: Iterable[bytes],
                     cancel_event: threading.Event | None = None,
                     prefix: str = "upload_") -> UploadResult: ...
```

- Input: session `cwd` plus client-relative path; A must not pass unchecked
  absolute client input as an authorization decision.
- Output: validated path, metadata, names, `UploadResult(path, bytes_written)`.
- Error: `FilesystemOperationError(operation, reply_code, message)`; cancellation
  is `TransferCancelledError(..., 426)`.
- Side effects: directory/file changes only inside `root_dir`; uploads use `.part`
  and `os.replace`.
- Thread safety: path locks serialize related writes/rename/delete; unrelated paths
  can proceed concurrently.
- Cleanup: C removes temporary files and releases path locks; A clears command state.
- FTP mapping: 501 invalid argument, 550 unsafe/unavailable path, 451 local
  failure, 426 cancelled transfer.

`FilesystemService` is the single filesystem boundary in the command handler and
transfer manager. Command formatting may inspect returned metadata, but path
resolution, file reads/writes and directory operations stay in the service.
**Status:** Existing and verified by filesystem, command and FTP E2E tests.

## 3. API Role A/C → Role B: transfer

**Module:** `server.transfer_manager.TransferManager` (A orchestration/C
filesystem boundary) and canonical RDT adapters. **Status:** Existing in both
test doubles and the production FTP path.

```python
class RDTReceiver(Protocol):
    def receive(self, data_socket: socket.socket,
                endpoint: Endpoint,
                context: TransferContext) -> Iterable[bytes]: ...

class RDTSender(Protocol):
    def send(self, chunks: Iterable[bytes],
             data_socket: socket.socket,
             endpoint: Endpoint,
             context: TransferContext) -> int: ...

class TransferManager:
    def upload(self, session: Session, filepath: str, *,
               data_socket: socket.socket, endpoint: Endpoint,
               context: TransferContext) -> TransferResult: ...
    def download(self, session: Session, filepath: str, *,
                 data_socket: socket.socket, endpoint: Endpoint,
                 context: TransferContext) -> TransferResult: ...
    def append(self, session: Session, filepath: str, *,
               chunks: Iterable[bytes], context: TransferContext) -> TransferResult: ...
    def upload_unique(self, session: Session, *, chunks: Iterable[bytes],
                      context: TransferContext) -> TransferResult: ...
    def cancel(self, session: Session) -> None: ...
```

- Input: validated operation/path, endpoint, socket, `TransferContext` and a
  cancellation event. B never receives an unvalidated client path.
- Output: `TransferResult`; upload returns committed bytes/path, download returns
  sent bytes/path.
- Error: no unbounded exception escapes; map protocol timeout/error to 426,
  endpoint failure to 425, filesystem errors to their structured code.
- Side effects: C commits/removes files; B sends/receives UDP; A maps result to TCP.
- Resource ownership: B owns RDT state and only a socket borrowed for one transfer;
  C owns file handles/temp files; A owns session and command reply.
- Cleanup: B closes/neutralizes worker-side UDP resources; C removes `.part`; A
  clears transfer state and sends final reply.

**Cần xác nhận — requirement yêu cầu production A/B/C transfer, code hiện tại
đang có `TransferManager` gọi `send/receive` adapter nhưng `common.rdt_sender`
và `common.rdt_receiver` expose filepath/save-path helpers khác signature.**

## 4. Context objects

```python
@dataclass
class Endpoint:
    host: str
    port: int
    mode: Literal["ACTIVE", "PASSIVE"]

@dataclass
class TransferContext:
    transfer_id: str
    operation: Literal["RETR", "STOR", "STOU", "APPE"]
    session_id: str
    endpoint: Endpoint
    cancel_event: threading.Event
    chunk_size: int
    timeout_seconds: float
    retry_limit: int
    max_timeouts: int
    window_size: int = 4
    total_bytes: int | None

@dataclass(frozen=True)
class TransferResult:
    success: bool
    reply_code: int
    bytes_transferred: int = 0
    path: str | None = None
    error: str | None = None
```

`transfer_id` is generated per transfer by the session/command lifecycle and is
copied into every RDT packet as a normalized unsigned 32-bit wire value.
**Status:** Existing and covered by protocol plus FTP E2E tests.

## 5. FTP reply mapping

| Event | Reply | Owner | Status |
|---|---:|---|---|
| Endpoint ready, transfer worker started | 150 | A | Existing |
| Commit/send/receive complete | 226 | A after B/C result | Existing |
| Endpoint cannot be selected/opened | 425 | A/B | Existing |
| Timeout, protocol error, ABOR/disconnect | 426 | A from result | Existing |
| Invalid/unsafe/missing path | 501 or 550 | C error, A mapping | Existing in C; A integration needed |
| Local transient filesystem error | 451 | C error, A mapping | Existing in C; integration needed |
| Unsupported MODE B/C | 502 | A | Existing behavior |
| Not authenticated | 530 | A | Existing in several handlers |

`150` must precede real data transfer; `226` is forbidden before RDT and atomic
commit finish.

## 6. Active/PASV endpoint contract

- `PORT h1,h2,h3,h4,p1,p2`: A parses exactly six decimal octets, validates
  `0..255`, rejects port 0, applies peer/IP policy, and stores `Endpoint(ACTIVE)`.
- `PASV`: A requests C/B endpoint allocation. The endpoint is UDP, not a legacy
  TCP data connection. A returns `227` with host/port and stores
  `Endpoint(PASSIVE)`.
- Old endpoint/socket is closed before replacement; QUIT/disconnect/ABOR closes it.
- B uses only the endpoint passed in `TransferContext`; B does not invent a second
  endpoint. C does not open a TCP data connection.
- For an ACTIVE download, the client emits a zero-payload RDT `START` probe to
  the negotiated server UDP endpoint after `150`. It creates the stateful
  UDP/NAT path for the server's real `START`; it carries no file payload and
  does not alter the FTP lifecycle.
- `FTPServer.advertised_host` overrides the bound address when a LAN server uses
  `--host 0.0.0.0`; old UDP sockets are closed before replacement.
- Status: localhost Active/PASV is verified. Two-machine LAN evidence remains a
  manual final-week task and must not be claimed until its artifacts are saved.

## 6.1 LIST/NLST transport decision

`LIST` and `NLST` are commands and their textual results are sent on the TCP
control channel. This follows the project requirement: every approved command
is transmitted over TCP control, every reply uses TCP control, and UDP is
reserved for actual file payload. The listing is metadata/command output, not a
file payload.

- `LIST [path]`: TCP reply contains the detailed name, size, type and
  permissions listing.
- `NLST [path]`: TCP reply contains the plain name-only listing.
- No UDP endpoint, RDT transfer ID, `150`, or `226` lifecycle is required for
  a listing beyond the existing textual command reply.
- Owner: A handles command/reply; C supplies the validated filesystem listing.

**Status:** Existing and aligned with
`planning/Project1_SocketProgramming_2026.md` §2.2–2.3.

## 7. RDT packet contract

**Required wire order:** network byte order (big endian), fixed header, then exactly
`payload_length` bytes. Current canonical format is `!IIIHIH` (20 bytes):

| Field | Width | Meaning |
|---|---:|---|
| transfer_id | 4 bytes | normalized unsigned transfer identity |
| sequence | 4 bytes | DATA/FIN sequence |
| acknowledgement | 4 bytes | ACK sequence |
| flags | 2 bytes | DATA, ACK, FIN, START or ABORT |
| payload_length | 2 bytes | exact payload bytes after header |
| checksum | 4 bytes | CRC/hash over agreed header fields + payload |

The checksum covers transfer ID, sequence, acknowledgement, flags, payload
length and payload. The project requirement does not prescribe transfer-ID width;
the fixed 32-bit normalized value preserves the established public API without a
wire-breaking header redesign.

Flags: `START`, `DATA`, `ACK`, `FIN`, `ABORT`; illegal combinations are dropped.
`START` carries transfer metadata; `DATA` carries bytes; `ACK` carries the exact
acknowledged sequence; `FIN` explicitly closes data; `ABORT` cancels.

Policy: sender accepts ACK only from the expected UDP peer, matching transfer ID
and valid checksum. `START` is ACKed and retried with a finite limit before data.
DATA/FIN uses Go-Back-N: at most four packets are in flight, ACK is cumulative,
and a timeout retransmits from the oldest unacknowledged packet. The receiver
validates length/checksum/peer/ID, delivers only the next sequence, re-ACKs the
last contiguous sequence for duplicates/future packets, and never writes a
duplicate.

## 8. Timeout, retry, FIN and cancellation

- Initial timeout, retry limit and receiver inactivity timeout are constants in
  `TransferContext`; all are finite and logged with transfer ID.
- DATA/ACK loss causes retransmission up to the limit, then `TransferResult(False,
  426, error=...)` and cleanup.
- FIN uses a closing state: receiver remains able to re-ACK a duplicate FIN until
  final close timeout; EOF is never inferred from a short payload.
- `cancel_event.set()` is the shared cancellation signal. `ABOR` also closes or
  wakes the UDP socket; B exits, C removes `.part`, A maps to 426.
- Progress callback:

```python
ProgressCallback = Callable[[str, int, int | None], None]
# transfer_id, acknowledged_or_committed_bytes, total_bytes
```

Core sender/receiver callbacks now use the same shape. Legacy file-helper
callbacks retain their older shapes for compatibility, while `FTPClient` uses
the normalized callback to report upload/download progress in the demo CLI.
**Status:** Existing; verified by CLI/server/E2E tests.

## 9. Socket, file and worker ownership

| Resource | Create/use | Close/delete | Status |
|---|---|---|---|
| TCP control socket | server/client handler | A/C on QUIT/disconnect/server stop | Existing partial |
| UDP transfer socket | endpoint owner agreed by A/B | B transfer finally + A session cleanup | Existing |
| Source file handle | C/filesystem iterator | C/context manager | Existing in service |
| `.part` target | C | C on commit failure/ABOR | Existing in service |
| Transfer worker | A/C orchestration | A/C join/cancel, B exits | Existing |
| Session registry entry | C server | C unregister exactly once | Existing |

No global client lock may be held while waiting for UDP ACK. All cleanup paths are
idempotent and bounded.

## 10. Logging and thread safety

Every command/transfer event logs timestamp, client IP, session ID, transfer ID,
operation, mode, result and byte count; password and file contents are never logged.
Registry/log locks protect shared structures only. Session fields are owned by one
client thread except `cancel_event`, which is the explicitly synchronized A/B/C
handoff. Server logging now records connected client IP, redacted command,
reply, session ID, transfer ID, active-session snapshot, transfer mode, byte
count and result. The demo client renders real upload/download progress.
**Status:** Existing; screenshots remain manual evidence.

## 11. Contract change procedure

1. Open a change entry with requirement ID, affected modules and compatibility risk.
2. Mark each affected API/header/reply as `Existing`, `Needs change` or `Proposed`.
3. A, B and C review signatures, ownership, cleanup and tests.
4. Update this file first, then role docs/report parts, then code/tests.
5. Add or update production-path tests and evidence; do not mark `Verified` from
   static inspection alone.
6. Record the decision and reviewer names in the change log below.

### Change log

| Date | Change | Decision/reviewers | Evidence |
|---|---|---|---|
| 2026-08-07 | Initial contract audit | Pending A/B/C confirmation | Source inspection; no code changed |
| 2026-08-08 | Implemented `TransferContext` and canonical adapters | A/B implementation; C filesystem boundary preserved | 52 Role A + 21 protocol + 14 fault tests pass |
| 2026-08-08 | Verified unchanged contract on WSL2 | A/C test repair; no API/header change | `python3 -m pytest -q`: 186 passed in 104.09s; saved evidence log |
| 2026-08-08 | RDT runtime failures now map to structured FTP `426` | C integration; no wire/API signature change | Production PASV ABOR and disconnect cleanup tests pass; full pytest: 189 passed in 113.94s |
| 2026-08-08 | Added configurable PASV advertised host for LAN demo | C integration; `FTPServer.advertised_host` is optional and backward compatible | `python3 -m server.threaded_server --help`; threaded + E2E: 10 passed in 21.56s |
| 2026-08-08 | Clarified LIST/NLST transport | A/B/C requirement decision: textual listing stays on TCP control; UDP is file payload only | Requirement §1.1–1.2, §2.2–2.3; existing command tests and full pytest 189 passed |
| 2026-08-08 | Normalized progress and server lifecycle logging | C integration; legacy file-helper callbacks remain backward compatible | Command/server/E2E/CLI: 62 passed; full pytest: 189 passed in 102.50s |
| 2026-08-08 | Added `TransferContext.total_bytes` for RETR progress | A/C/B compatible optional field; sender places it in RDT START | E2E progress-total assertion: 5 passed in 17.61s; full pytest: 189 passed in 106.91s |
| 2026-08-09 | Go-Back-N flow control and reliable START lifecycle | C implementation; header layout and public adapter signatures preserved; B review pending | Protocol 27 passed; fault/transfer/E2E 22 passed; full WSL2 pytest 192 passed in 91.11s |
