# Hybrid FTP

Hybrid FTP uses TCP for the control channel and UDP through a custom Reliable
Data Transfer (RDT) protocol for file payloads. The project runs on Python 3
under Linux or WSL2.

## Run and test

From the repository root:

```bash
python -m pip install pytest
python -m pytest -v
python -m server.threaded_server
```

The server listens on `127.0.0.1:2121` by default. Stop it with `Ctrl+C`.

### Two-machine LAN demo

On the server machine, replace `192.168.x.x` with its actual LAN IPv4 address:

```bash
python -m server.threaded_server --host 0.0.0.0 --port 2121 --advertise-host 192.168.x.x
```

On a client machine on the same network:

```bash
python -m client.demo_transfer demo.bin --remote demo-lan.bin --mode PASV --host 192.168.x.x --port 2121
```

Open TCP/UDP port 2121 in the firewall when necessary, then save terminal
output, SHA-256 values, and logs in `docs/evidence/`. A two-machine LAN demo is
complete only when real artifacts exist; localhost E2E and LAN are separate
evidence scopes.

## Directory structure

```text
.
├── client/                     # FTP client and CLI demo
├── server/                     # TCP server, command/session/transfer handling
├── common/                     # Shared RDT, protocol, and filesystem helpers
├── tests/                      # Pytest unit, fault-injection, and E2E tests
├── docs/                       # Contract, evidence, status, checklist, and report
│   ├── project-status.md       # Source of truth for current status
│   ├── requirement-checklist.md# Pre-submission acceptance gates
│   ├── api-contract.md         # Shared A/B/C contract
│   ├── report.md               # Final report — maintained by Role B
│   ├── report-parts/           # Technical and submission drafts
│   └── evidence/               # Verified logs and hashes
└── planning/                   # Requirements, ownership, and weekly plans
    ├── Project1_SocketProgramming_2026.md  # Original requirement; read-only
    ├── Socket Role.md                       # Original ownership document
    ├── status/                              # Links to project status
    └── weekly-plans/                        # Week 1, 2, 2.5, and final snapshots
```

## Documentation rules

- `planning/reference/Project1_SocketProgramming_2026.md`: original requirement; do not update progress here.
- `docs/project-status.md`: the sole status source (`Done`, `In progress`, `Deferred`).
- `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md`: daily dashboard with owner, deadline, blocker, and evidence.
- `docs/requirement-checklist.md`: pre-submission acceptance review; every `Done` claim needs evidence.
- `docs/report.md`: final report compiled by Role B; Roles A/C sign off their technical sections.
- `docs/report-parts/`: drafts/history; do not use to determine current status.

## Git conventions

- `main`: stable code; merge through a reviewed pull request.
- `dev`: shared integration branch.
- `feature/role-a`, `feature/role-b`, `feature/role-c`: role-specific branches.
- Commit message: `[role][module] short description`, for example `[A][auth] implement USER/PASS command`.

Before committing moved documentation, run:

```bash
git add -A
git status --short --branch --untracked-files=all
git diff --check
```

`git add -A` lets Git recognize renamed files across `filephanchiacv/`,
`planning/`, and `docs/report-parts/`.
