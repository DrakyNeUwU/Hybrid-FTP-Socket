# Technical Report — Hybrid FTP

> This document follows the seven mandatory sections in Section 2.4 of the
> project specification. Each member completes the sections related to their
> implementation.

## 1. Application Scenario & Protocol Interaction

The Hybrid FTP system uses two independent channels. The TCP control channel
carries commands, FTP replies, and session state. The UDP data channel carries
file payloads through a custom Reliable Data Transfer (RDT) layer developed by
the team.

After a TCP client connects, the server sends `220 Hybrid FTP Server Ready`. The
client authenticates with `USER` followed by `PASS`. After successful login, the
client may issue control commands. The server parses each request, validates the
session state, performs the operation, and returns the corresponding FTP reply.
`QUIT` ends the session and closes the control connection safely.

The complete TCP-plus-UDP sequence diagram will be finalized during integration.
Role A owns the TCP lifecycle, Role B adds UDP DATA/ACK/retransmission behavior,
and Role C verifies threading, filesystem operations, and cleanup against the
integrated implementation.

## 2. Project-Wide Data Structures

### 2.1 FTP Control Command Format (Role A)

A command on the TCP control channel has this form:

```text
COMMAND [argument]\r\n
```

`COMMAND` is an FTP command name and `argument` is optional. Examples:

```text
USER admin
PASS 123456
CWD test
MKD demo
```

After receiving data from the TCP socket, the server uses `parse_command()` to
separate the command and argument before dispatching to a command handler. Every
response returns over the same TCP connection as a three-digit FTP reply code
with a descriptive message.

### 2.2 Session Structure (Role A)

Every client owns an independent `Session` that stores authentication and
working-directory state:

```python
class Session:
    def __init__(self):
        self.username = None
        self.is_logged_in = False
        self.current_dir = os.getcwd()
```

| Attribute | Meaning |
|---|---|
| `username` | Account name currently used during authentication |
| `is_logged_in` | Whether the client has authenticated successfully |
| `current_dir` | Current working directory for this session |

Separate sessions allow a thread-per-client model without sharing client state.
Integration will extend this structure with transfer type, Active/PASV endpoint,
rename state, and current transfer state.

### 2.3 RDT Header (Role B)

_(Role B will add a byte-level table containing the sequence number, ACK,
checksum, flags, and payload length.)_

## 3. Functional Workflows (Flowcharts)

### 3.1 Authentication Workflow (Role A)

```mermaid
flowchart TD
    Connect["Client opens TCP connection"] --> Banner["Server replies 220 Service Ready"]
    Banner --> User["Client sends USER username"]
    User --> ValidUser{"Valid username?"}
    ValidUser -- "No" --> UserFail["530 Invalid username"]
    ValidUser -- "Yes" --> NeedPass["Store username and reply 331 Need password"]
    NeedPass --> Pass["Client sends PASS password"]
    Pass --> ValidPass{"Valid password?"}
    ValidPass -- "No" --> PassFail["530 Login incorrect"]
    ValidPass -- "Yes" --> LoggedIn["Set is_logged_in = True"]
    LoggedIn --> Success["230 Login successful"]
```

If a client sends `PASS` before `USER`, the server replies
`503 Login with USER first`. Commands that require access return
`530 Not logged in` until authentication succeeds.

### 3.2 FTP Command Processing Workflow (Role A)

```mermaid
flowchart TD
    Receive["Receive data with recv()"] --> Parse["parse_command()"]
    Parse --> Known{"Supported command?"}
    Known -- "No" --> NotImplemented["502 Command not implemented"]
    Known -- "Yes" --> NeedAuth{"Authentication required?"}
    NeedAuth -- "No" --> Dispatch["Call command handler"]
    NeedAuth -- "Yes" --> Authenticated{"Session authenticated?"}
    Authenticated -- "No" --> NotLoggedIn["530 Not logged in"]
    Authenticated -- "Yes" --> Dispatch
    Dispatch --> Reply["Send FTP reply over TCP"]
```

Every command is parsed and checked for valid syntax and session state before
dispatch. The handler returns a result that the control channel maps to an FTP
reply. Invalid input must not terminate the client thread or server.

### 3.3 Thread-Dispatch Workflow (Role C)

The multithreaded server architecture serves multiple clients concurrently
without one client blocking another.

```mermaid
flowchart TD
    Start(["Start FTPServer.start()"]) --> BindListen["Bind IP/port and call listen(5)"]
    BindListen --> TimeoutSet["Set socket timeout to 0.5 seconds"]
    TimeoutSet --> LoopAccept{"Continue accept loop?<br/>is_running == True"}

    LoopAccept -- "No" --> StopServer["Close server socket and client threads"]
    StopServer --> End(["Server stopped"])

    LoopAccept -- "Yes" --> TryAccept["Wait for client with accept()"]
    TryAccept -- "Timeout" --> LoopAccept
    TryAccept -- "New client" --> SpawnThread["Create ClientHandler thread"]

    SpawnThread --> RegClient["Register client under active-client lock"]
    RegClient --> StartThread["Call ClientHandler.start()"]
    StartThread --> LoopAccept

    subgraph PerClientThread ["Per-client ClientHandler.run()"]
        InitClient["Send 220 Service Ready"] --> LoopRecv{"Continue recv loop?<br/>is_running == True"}
        LoopRecv -- "Data received" --> ParseCmd["Parse FTP command"]
        ParseCmd -- "QUIT" --> Send221["Send 221 Goodbye"]
        Send221 --> CloseClient["Close socket and unregister client"]
        ParseCmd -- "Other command" --> ProcessCmd["Process Echo/Filesystem/RDT operation"]
        ProcessCmd --> SendResp["Send reply code"]
        SendResp --> LoopRecv
        LoopRecv -- "Disconnect or error" --> CloseClient
        CloseClient --> ExitThread(["Client thread exits"])
    end

    StartThread -.-> InitClient
```

#### Thread-dispatch details

1. **Main thread:**
   - Listens for TCP connections on the default port, 2121.
   - Uses `socket.settimeout(0.5)` so `accept()` periodically unblocks and checks
     `is_running`, enabling graceful shutdown.
   - Creates a `ClientHandler`, registers it, and calls `.start()` for every new
     connection.
2. **Client thread:**
   - Each client has an independent thread and connection state.
   - On disconnect or `QUIT`, the handler calls
     `shutdown(socket.SHUT_RDWR)`, closes the socket, and removes itself from
     `active_clients` under a lock.
   - Server shutdown snapshots the client list, releases the registry lock,
     cleans up clients, and joins their threads. Releasing the lock before
     cleanup prevents a deadlock when a handler unregisters itself.

### 3.4 Path Validation and Security Sandbox (Role C)

This workflow prevents path-traversal attacks, such as a client sending
`CWD ../../etc/passwd` to access data outside the FTP root.

```mermaid
flowchart TD
    ClientReq["Client sends command containing a path<br/>CWD, RETR, LIST, MKD, DELE, etc."] --> ResolvePath["resolve_path(base_dir, cwd, input_path)"]
    ResolvePath --> CheckAbs{"FTP-absolute path?<br/>Starts with /"}
    CheckAbs -- "Yes" --> JoinBase["Remove leading slash and join with base_dir"]
    CheckAbs -- "No" --> JoinCWD["Join with current CWD"]
    JoinBase --> RealPath["Call os.path.realpath()<br/>Resolve symlinks, dots, and parent segments"]
    JoinCWD --> RealPath
    RealPath --> ValidatePath{"Inside real FTP root?"}
    ValidatePath -- "No" --> RaisePermErr["Raise PermissionError"]
    RaisePermErr --> Reply550["Return 550 Requested action not taken"]
    ValidatePath -- "Yes" --> ExecuteFS["Perform filesystem operation"]
    ExecuteFS --> ReplySuccess["Return success reply such as 200, 250, or 257"]
```

#### Sandbox details

1. **Path normalization:** `os.path.realpath()` resolves `..`, `.`, and symbolic
   links before access.
2. **Boundary enforcement:** The resolved target must equal the FTP root or
   begin with `real_base + os.sep`. Including the separator prevents
   `/ftp_root_backup` from matching `/ftp_root`.
3. **FTP error mapping:** An outside path is rejected and mapped to
   `550 Requested action not taken`.
4. **Symlink listings:** `LIST` and `NLST` omit entries whose resolved targets
   leave the FTP root.

### 3.5 Atomic Upload and File Locking (Role C)

```mermaid
flowchart TD
    Request["STOR, STOU, or APPE request"] --> Resolve["Resolve and validate target path"]
    Resolve --> Lock["Acquire per-path lock"]
    Lock --> Temp["Create hidden .part file in target directory"]
    Temp --> Cancelled{"Transfer cancelled?"}
    Cancelled -- "Yes" --> Remove["Delete .part file and keep old target"]
    Cancelled -- "No" --> Write["Write binary chunks"]
    Write --> More{"More chunks?"}
    More -- "Yes" --> Cancelled
    More -- "No" --> Flush["Flush and fsync"]
    Flush --> Replace["Atomically replace target"]
    Replace --> Unlock["Release path lock"]
```

`STOR` replaces an existing file only after all data is written successfully.
`APPE` copies the existing content into the temporary file and appends new
chunks while holding one path lock, preventing concurrent clients from mixing
bytes. `STOU` generates a unique server-side name. A cancellation maps to reply
`426`; path errors map to `550`; invalid parameters map to `501`; and other local
filesystem failures map to `451`.

### 3.6 RDT Sender/Receiver State Machines (Role B)

_(Role B will complete this section.)_

### 3.7 Active/Passive Mode Workflow (Roles A, B, and C)

_(This section will be completed after the Week 2 integration.)_

## 4. Task Assignment Matrix

| Module or component | Owner | Collaborators |
|---|---|---|
| TCP server/client control connection | Role A | Role C (integration and review) |
| FTP command parser and reply handling | Role A | Role C (review) |
| Authentication (`USER`, `PASS`) | Role A | — |
| Session management | Role A | Role C (thread/session integration) |
| UDP data channel and RDT | Role B | Roles A and C (integration) |
| Filesystem and path sandbox | Role C | Role A (command integration) |
| Multithreaded server and active-session registry | Role C | Roles A and B (review) |
| End-to-end integration | Role C | Roles A and B |
| TCP-plus-UDP sequence diagram | Roles A and B | Role C (code verification) |
| RDT state machines and header table | Role B | — |
| Thread dispatch, path validation, and file lifecycle diagrams | Role C | — |

This matrix will be updated using commit history and the final implementation
before submission.

## 5. Self-Assessment & Peer Evaluation

### 5.1 Role A — Self-Assessment

Role A implemented the TCP control channel, command parser, user authentication,
and basic session management. The `USER`, `PASS`, `QUIT`, and `NOOP` flows and
invalid authentication cases use FTP reply codes. Session state is separated in
preparation for concurrent clients.

Role A must compare this description with the final code after all commands,
Active/PASV negotiation, and the UDP transfer lifecycle are integrated.

### 5.2 Role B — Self-Assessment

_(Role B will add the UDP/RDT assessment.)_

### 5.3 Role C — Self-Assessment

Role C implemented binary-safe file helpers, FTP-root path confinement,
directory and metadata operations, a structured filesystem integration API,
atomic uploads, per-path locks, transfer cancellation cleanup, a multithreaded
server, active-session snapshots, and safe operational logging. Unit and socket
tests cover independent paths, traversal attempts, concurrent append, unique
names, cancellation, and server shutdown.

The current branch does not yet contain the final Role A and Role B modules, so
full TCP-plus-UDP upload/download behavior remains unverified. Role C will lead
that integration and collect end-to-end evidence after both modules are merged.

### 5.4 Peer Evaluation

_(The team must agree on contribution percentages totaling 100%.)_

## 6. GenAI Usage & Code Refinement Log

GenAI is used for reference and review. Every member must inspect, understand,
test, and refine generated material before integrating it. Exact prompts, raw
output, and manual refinements are stored in:

- Role A: `docs/genai-log-a.md`
- Role B: `docs/genai-log-b.md`
- Role C: `docs/genai-log-c.md`

The final appendix must include or attach these logs. A general summary in this
report does not replace exact prompts and raw output.

## 7. Application Demo Evidence

### 7.1 TCP Control and Authentication (Role A)

The TCP control test uses the project client or Netcat (`nc`) to:

1. Open a TCP connection and receive the `220` banner.
2. Log in with `USER` and `PASS`.
3. Test an invalid username, invalid password, and `PASS` before `USER`.
4. Send `NOOP` and other implemented control commands.
5. Send `QUIT`, receive `221`, and confirm safe session cleanup.

Role A's report must include actual terminal output or screenshots before final
submission. The server should return the expected FTP replies without crashing
on invalid authentication input.

### 7.2 Filesystem and Concurrency Evidence (Role C)

On August 3, 2026, `py -m pytest -v` collected 90 tests and reported
`89 passed, 1 skipped` without warnings. Covered behavior includes binary file
handling, directory operations, path traversal, atomic upload, cancellation,
concurrent append, unique STOU names, ten concurrent TCP clients, and shutdown
with a connected client. The skipped symlink test requires privileges not
available in the Windows test environment.

### 7.3 UDP Transfer and End-to-End Evidence

_(After integration, Role C will add upload/download screenshots, SHA-256
comparisons, and active-session/concurrent-client logs. Role B will provide RDT
fault-injection evidence.)_
