# Code Change History — Hybrid FTP

This history records evidence-backed changes. It does not replace end-to-end
demo evidence or `docs/project-status.md`.

## Week 1 — Foundation and module split

| Role | Work | Result |
|---|---|---|
| A | Split TCP server, parser, command handler, and session | Per-client command-processing structure |
| B | Created basic RDT header, sender, and receiver | Sequence, ACK, checksum, and FIN support |
| C | Built filesystem helpers/service and FTP root | Binary-safe file handling and basic path safety |

## Week 2 — Core functions

| Role | Work | Result |
|---|---|---|
| A | Added login, directory commands, PORT/PASV, RETR/STOR, and replies | Expanded TCP command matrix |
| B | Added retransmission, duplicate handling, and checksums | Basic Stop-and-Wait RDT |
| C | Added root confinement, atomic upload, and metadata | Filesystem cannot write outside the FTP root |

## Week 2.5 and final week — Integration and verification

The team added transfer guards, a shared `TransferContext`, strict RDT
flag/length/checksum/peer/transfer-ID validation, bounded receiver timeouts,
atomic failure/cancellation cleanup, Active/PASV end-to-end tests, concurrent
PASV-client coverage, ABOR/disconnect cleanup, LAN endpoint configuration, CLI
progress, server log redaction, total-size progress reporting, and Go-Back-N
window four with START ACK/retry.

Final evidence includes `python3 -m pytest -q` — **199 passed in 96.72s**,
protocol/fault/E2E evidence, and two-machine LAN source/server/client SHA-256
artifacts. See `docs/evidence/final-week-rdt-gbn-verification.md` and the
curated files under `docs/evidence/`.
