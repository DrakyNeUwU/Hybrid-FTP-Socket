# Hybrid FTP

Hybrid FTP uses TCP for FTP-like control commands and UDP through a custom
Reliable Data Transfer (RDT) protocol for file payloads. It runs on Python 3
under Linux or WSL2.

## Quick start

Run all commands from the repository root. Install the only test dependency:

```bash
python -m pip install pytest
```

Start a local server in terminal 1. `--ftp-root` is the directory exposed to
FTP clients; it is created when needed.

```bash
python -m server.threaded_server --host 127.0.0.1 --port 2121 --ftp-root ./ftp_root
```

In terminal 2, upload then download one local binary-safe file. The demo uses
the configured development account internally; do not place passwords in
screenshots or committed logs.

```bash
# Replace demo.bin with an existing local file.
python -m client.demo_transfer demo.bin --remote demo-s.bin --mode PASV --transfer-mode S
```

The demo reports the control replies and validates the upload/download
round-trip. Stop the server with `Ctrl+C` after the client exits.

## Transfer modes and data-channel modes

`--mode` selects how the client establishes the UDP data endpoint:

- `PASV`: the server advertises a UDP endpoint; this is the usual choice.
- `ACTIVE`: the client supplies a reachable UDP endpoint; use it only when the
  server can reach the client through the firewall/NAT.

`--transfer-mode` selects the negotiated FTP `MODE` used by the real transfer
path:

- `S`: stream framing.
- `B`: block framing.
- `C`: compressed framing (the implementation uses a reversible literal/run
  encoding for binary-safe transfer).

Run these one at a time while the server is running:

```bash
# PASV + MODE B
python -m client.demo_transfer demo.bin --remote demo-b.bin --mode PASV --transfer-mode B

# ACTIVE + MODE C
python -m client.demo_transfer demo.bin --remote demo-c.bin --mode ACTIVE --transfer-mode C
```

Use a fresh remote name for every demo. The server accepts `MODE S`, `MODE B`,
and `MODE C`; a successful reply alone is not proof of support—the upload and
download must complete with the selected mode.

## LAN demo

On the server machine, replace `192.168.x.x` with its actual LAN IPv4 address.
The advertised address is required for PASV clients on another machine.

```bash
python -m server.threaded_server --host 0.0.0.0 --port 2121 --ftp-root ./ftp_root --advertise-host 192.168.x.x
```

On a client machine on the same network:

```bash
python -m client.demo_transfer demo.bin --remote demo-lan-b.bin --mode PASV --transfer-mode B --host 192.168.x.x --port 2121
python -m client.demo_transfer demo.bin --remote demo-lan-c.bin --mode ACTIVE --transfer-mode C --host 192.168.x.x --port 2121
```

Open the control TCP port and the required UDP traffic in the firewall. A
localhost E2E result and a two-machine LAN result are separate evidence scopes.

## Control-command usage

The demo program is intentionally a transfer demo. For manual control-command
checks, use `FTPClient.command()` in a Python shell after the server has
started:

```python
from client.ftp_client import FTPClient

client = FTPClient("127.0.0.1", 2121)
print(client.connect().strip())
client.login()                         # configured development account
print(client.command("PWD").strip())
print(client.command("HELP MODE").strip())
print(client.command("STAT").strip())
print(client.command("TYPE I").strip())
print(client.command("MODE B").strip())
print(client.command("QUIT").strip())
client.close()
```

Common command syntax is below. Commands that transfer payloads should normally
be invoked through `upload_file()` or `download_file()` (or
`client.demo_transfer`), because they also set up the required UDP endpoint.

| Purpose | TCP command |
|---|---|
| Authenticate | `USER <username>`, then `PASS <password>` |
| Directory/listing | `PWD`, `CWD <path>`, `LIST [path]`, `NLST [path]` |
| File metadata | `STAT [path]`, `SIZE <path>`, `MDTM <path>`, `HASH <path>` |
| Transfer options | `TYPE A` or `TYPE I`; `MODE S`, `MODE B`, or `MODE C` |
| Data endpoint | `PASV` or `PORT h1,h2,h3,h4,p1,p2` (normally client-managed) |
| File operations | `STOR <name>`, `RETR <name>`, `STOU [name]`, `APPE <name>` |
| Session/help | `ABOR`, `HELP [command]`, `QUIT` |

`TYPE I` is the appropriate default for binary files. `ABOR` cancels an active
transfer; an interrupted upload must not publish a partial final file.

## Test commands

Run the whole regression suite before a release:

```bash
python -m pytest -v
```

Useful focused checks:

```bash
python -m pytest tests/test_threaded_server.py -v
python -m pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -v
python -m pytest tests/test_e2e_transfer.py -v
```

Test names can evolve; list the available tests with
`python -m pytest --collect-only -q` if a focused path does not exist in the
current branch.

## Demo evidence checklist

Save only reproducible terminal logs, hashes, and screenshots under
`docs/evidence/`. The exact final-evidence filenames and acceptance checks are
maintained in
[`planning/weekly-plans/final-code-fix-a-c.md`](planning/weekly-plans/final-code-fix-a-c.md).

For each upload/download proof, record the source, server-side, and downloaded
file hashes. Use the command appropriate to the machine:

```powershell
Get-FileHash .\demo.bin -Algorithm SHA256
```

```bash
sha256sum demo.bin
```

Also record the commit being demonstrated:

```bash
git rev-parse --short HEAD
```

Do not include passwords, credentials, or failed server-start traces in final
screenshots. A server log should visibly show the client IP, executed commands,
and active-session state for the concurrent-session evidence.

## Directory structure

```text
.
├── client/                     # FTP client and transfer-demo CLI
├── server/                     # TCP server, command/session/transfer handling
├── common/                     # Shared RDT, protocol, and filesystem helpers
├── tests/                      # Pytest unit, fault-injection, and E2E tests
├── docs/                       # Contract, evidence, status, checklist, report
│   ├── project-status.md       # Source of truth for current status
│   ├── requirement-checklist.md# Pre-submission acceptance gates
│   ├── api-contract.md         # Shared A/B/C contract
│   ├── report.md               # Final report — maintained by Role B
│   ├── report-parts/           # Technical and submission drafts
│   └── evidence/               # Verified logs and hashes
└── planning/                   # Requirements, ownership, and weekly plans
    ├── reference/Project1_SocketProgramming_2026.md # Original requirement
    ├── reference/Socket Role.md                      # Ownership document
    └── weekly-plans/                                 # Current execution plans
```

## Documentation and Git rules

- `planning/reference/Project1_SocketProgramming_2026.md` is read-only; do not
  update progress there.
- `docs/project-status.md` is the single current-status source. Do not claim
  `Done` without a real test, log, hash, or review record.
- `docs/requirement-checklist.md` is the pre-submission acceptance gate.
- `docs/report.md` is the report assembled by Role B; Roles A/C technically
  review their own sections.
- `docs/report-parts/` is draft/history, not the current status source.

Before committing documentation or code, inspect exactly what will be included:

```bash
git status --short --branch --untracked-files=all
git diff --check
git diff --cached --check
```

Use a scoped commit message such as `[A][transfer] verify MODE B production
path`. Do not commit runtime transfer data, caches, local paths, credentials, or
unverified screenshots.
