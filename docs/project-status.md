# Project Status — Hybrid FTP

**Source of truth for current status.**
**Updated:** 10/08/2026

| Item | Status | Final owner | Evidence / blocker |
|---|---|---|---|
| TCP control, parser, session, command lifecycle | Integrated | A; C review | Strict auth, STAT/HELP/STOU and buffered client framing verified; screenshots/release review pending |
| MODE S/B/C functional codec + integration | Integrated | A; C review | MODE/TYPE START validation, atomic client/server paths and 271-pass regression verified; B review/A screenshots pending |
| UDP/RDT Go-Back-N window 4 and integrity | Done | C/B | START ACK/retry; protocol, fault, and E2E tests |
| Filesystem sandbox, atomic upload, cleanup, concurrency | Done | C | Shared server locks, same-file APPE, three clients, ABOR and disconnect |
| Active/PASV localhost and two-machine LAN | Done | C | Matching source/server/client SHA-256 artifacts |
| Final report, peer evaluation, and contribution percentages | In progress | B | Team percentage and release sign-off are pending |
| Oral preparation and clean Git release check | In progress | B | Release check is pending |

## Verified facts

- Post-handoff WSL2 regression: `python3 -m pytest -q` — **205 passed in
  103.08s**; Role C focused regression — **24 passed in 33.80s**.
- Full regression after Role A MODE S/B/C: `python3 -m pytest -q` —
  **271 passed, 357 subtests in 192.88s** after production review hardening.
- Production audit reproduced silent MODE mismatch corruption, client destination
  deletion, TCP framing and command gaps. C applied the integration fixes; see
  `docs/evidence/role-a-production-review-2026-08-10.md`. Role B START-metadata
  review and Role A screenshots remain pending, so these rows are not Accepted.
- MODE behavior now functional: `MODE S → 200 Mode Stream`,
  `MODE B → 200 Mode Block`, `MODE C → 200 Mode Compressed`; invalid/missing/
  unauthenticated return `501`/`530` without changing session mode.
  Implementation: `common/mode_codec.py`, `server/command_handler.py`,
  `server/transfer_manager.py`, `client/ftp_client.py`.
- Protocol verification: `tests/test_rdt.py` — **27 passed in 14.76s**.
- Fault, transfer-manager, and FTP E2E verification — **22 passed in 70.44s**;
  expanded FTP E2E — **6 passed in 22.63s**; MODE E2E matrix (PASV/ACTIVE S/B/C,
  STOU/APPE block, concurrent different-mode clients, progress logical bytes) —
  **13 passed, 8 subtests in 77.13s** (thêm server-stop mid-B-upload).
- Active and PASV localhost/LAN SHA-256 values match across source, server, and
  client artifacts under `docs/evidence/`.

Update this document only when real status changes. Every `Done` claim must
have command, log, hash, screenshot, or other concrete evidence.
