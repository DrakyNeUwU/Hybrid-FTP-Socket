# Project Status — Hybrid FTP

**Source of truth for current status.**
**Updated:** 09/08/2026

| Item | Status | Final owner | Evidence / blocker |
|---|---|---|---|
| TCP control, parser, session, command lifecycle | Done | A | Full suite and FTP E2E evidence |
| UDP/RDT Go-Back-N window 4 and integrity | Done | C/B | START ACK/retry; protocol, fault, and E2E tests |
| Filesystem sandbox, atomic upload, cleanup, concurrency | Done | C | FTP E2E with three PASV clients, ABOR, and disconnect |
| Active/PASV localhost and two-machine LAN | Done | C | Matching source/server/client SHA-256 artifacts |
| Final report, peer evaluation, and contribution percentages | In progress | B | Team percentage and release sign-off are pending |
| Oral preparation and clean Git release check | In progress | B | Release check is pending |

## Verified facts

- Final WSL2 regression: `python3 -m pytest -q` — **199 passed in 96.72s**;
  `docs/evidence/final-week-rdt-gbn-verification.md`.
- Protocol verification: `tests/test_rdt.py` — **27 passed in 14.76s**.
- Fault, transfer-manager, and FTP E2E verification — **22 passed in 70.44s**;
  expanded FTP E2E — **6 passed in 22.63s**.
- Active and PASV localhost/LAN SHA-256 values match across source, server, and
  client artifacts under `docs/evidence/`.

Update this document only when real status changes. Every `Done` claim must
have command, log, hash, screenshot, or other concrete evidence.
