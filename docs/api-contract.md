# Shared API Contract — Hybrid FTP

**Nguồn chuẩn duy nhất cho A–B–C:** tài liệu này.  
**Trạng thái:** contract được chốt ở mức tài liệu; phần ghi `Proposed` hoặc
`Needs change` chưa được xem là đã triển khai.  
**Nguồn requirement:** `docs/requirement-checklist.md` và
`filephanchiacv/Project1_SocketProgramming_2026.md`.

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

`FilesystemService` methods are `Existing` in C code. **Cần xác nhận — requirement
yêu cầu mọi A command dùng filesystem service, code hiện tại đang để
`server/command_handler.py` gọi `os.path`/`open`/`os.listdir` trực tiếp.**

## 3. API Role A/C → Role B: transfer

**Module:** `server.transfer_manager.TransferManager` (A orchestration/C
filesystem boundary) and a B adapter. **Status:** `Existing` test-double
boundary; `Needs change` for production adapter.

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

@dataclass(frozen=True)
class TransferResult:
    success: bool
    reply_code: int
    bytes_transferred: int = 0
    path: str | None = None
    error: str | None = None
```

`transfer_id` is generated by A/C per transfer and copied into every RDT packet.
It must be unique at least within the server lifetime. The current `Session` has
no formal transfer ID and `RDTHeader` has no transfer ID: `Needs change`.

## 5. FTP reply mapping

| Event | Reply | Owner | Status |
|---|---:|---|---|
| Endpoint ready, transfer worker started | 150 | A | Needs change |
| Commit/send/receive complete | 226 | A after B/C result | Needs change |
| Endpoint cannot be selected/opened | 425 | A/B | Needs change |
| Timeout, protocol error, ABOR/disconnect | 426 | A from result | Needs change |
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
- Status: `Needs change`; current handler creates a UDP socket for PASV but always
  advertises `127.0.0.1`, does not replace old socket safely, and Active/PASV is not
  end-to-end verified.

## 7. RDT packet contract

**Required wire order:** network byte order (big endian), fixed header, then exactly
`payload_length` bytes. Proposed canonical format (not yet current code):

| Field | Width | Meaning |
|---|---:|---|
| version/flags | 1/1 byte | protocol version and packet flags |
| transfer_id | 16 bytes | UUID/opaque transfer identity |
| sequence | 4 bytes | DATA/FIN sequence |
| acknowledgement | 4 bytes | ACK sequence |
| payload_length | 2 bytes | exact payload bytes after header |
| checksum | 4 bytes | CRC/hash over agreed header fields + payload |

The exact byte layout is `Proposed` and must be approved before implementation;
current `common/RDTHeader.py` is 16 bytes (`!IIHIH`), has no transfer ID/version,
and checksum covers payload only. **Cần xác nhận — requirement yêu cầu header có
sequence/ACK/checksum/flags/length, nhưng không quy định transfer_id width; team
phải xác nhận layout trước khi code.**

Flags: `START`, `DATA`, `ACK`, `FIN`, `ABORT`; illegal combinations are dropped.
`START` carries transfer metadata; `DATA` carries bytes; `ACK` carries the exact
acknowledged sequence; `FIN` explicitly closes data; `ABORT` cancels.

Policy: sender accepts ACK only from expected UDP peer, matching transfer ID,
sequence and valid checksum. Receiver validates packet length/checksum/peer/ID,
delivers only the next sequence, re-ACKs an old duplicate without writing it, and
drops future/out-of-order packets without advancing. Current B code violates the
last ACK ordering rule: `Needs change`.

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

Current sender/receiver callback shapes differ (`(transferred,total)` vs
`(len(payload))`): `Needs change`.

## 9. Socket, file and worker ownership

| Resource | Create/use | Close/delete | Status |
|---|---|---|---|
| TCP control socket | server/client handler | A/C on QUIT/disconnect/server stop | Existing partial |
| UDP transfer socket | endpoint owner agreed by A/B | B transfer finally + A session cleanup | Needs change |
| Source file handle | C/filesystem iterator | C/context manager | Existing in service |
| `.part` target | C | C on commit failure/ABOR | Existing in service |
| Transfer worker | A/C orchestration | A/C join/cancel, B exits | Needs change |
| Session registry entry | C server | C unregister exactly once | Existing partial |

No global client lock may be held while waiting for UDP ACK. All cleanup paths are
idempotent and bounded.

## 10. Logging and thread safety

Every command/transfer event logs timestamp, client IP, session ID, transfer ID,
operation, mode, result and byte count; password and file contents are never logged.
Registry/log locks protect shared structures only. Session fields are owned by one
client thread except `cancel_event`, which is the explicitly synchronized A/B/C
handoff. Current server has timestamp/redaction/session snapshots, but command and
transfer IDs are not consistently logged: `Needs change`.

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
