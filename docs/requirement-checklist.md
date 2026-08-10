# Requirement Acceptance Checklist — Hybrid FTP

**Audit date:** 10/08/2026
**Requirement source:** `planning/reference/Project1_SocketProgramming_2026.md`
**Current status source:** `docs/project-status.md`

| Requirement / acceptance gate | Status | Owner | Evidence |
|---|---|---|---|
| TCP control, replies, authentication, MODE S/B/C, and session isolation | In progress | A | MODE S/B/C functional and tested; strict auth, STAT/HELP/STOU and client framing still pending A |
| Commands, filesystem routing, and FTP-root safety | In progress | A/C | C filesystem scope verified; A command compliance re-verification pending |
| UDP/RDT ACK, retry, checksum, FIN, and Go-Back-N | Done | B/C | Protocol and fault tests |
| Active/PASV upload and download | Done | A/B/C | Localhost and LAN SHA-256 evidence; current post-handoff regression passes |
| Multi-client isolation, ABOR, and disconnect cleanup | Done | C | Shared-service, same-file APPE and FTP E2E evidence |
| CLI progress and redacted server logging | Done | C | CLI and LAN logs |
| Final report, contribution matrix, peer assessment, GenAI logs | In progress | B | Team contribution and release decision pending |
| Oral preparation and Git release hygiene | In progress | B | Clean release check pending |

## MODE S/B/C acceptance evidence (Role A, 10/08/2026)

- Exact command replies: `MODE S/B/C → 200 Mode Stream/Block/Compressed`;
  invalid `MODE X`, missing argument and unauthenticated return `501`/`530`
  without changing the session mode. Tests: `tests/test_commands.py`.
- Codec round-trip: empty, one-byte, random binary, text, repeated runs and
  boundaries 63/64, 127/128, 65535/65536. Tests: `tests/test_mode_codec.py`.
- Production path: encode before RDT, decode after RDT checksum/order, atomic
  `.part`, APPE/STOU decode, PASV/ACTIVE S/B/C SHA-256 round-trips, concurrent
  different-mode clients. Tests: `tests/test_transfer_manager.py`,
  `tests/test_e2e_transfer.py`.
- Reliability: B/C-encoded payloads recover under loss/corruption/ACK-loss via
  RDT; malformed stream returns 426 with no partial file. Tests:
  `tests/test_rdt_fault_injection.py`, `tests/test_transfer_manager.py`.
- Full regression: `python3 -m pytest -q` — **256 passed, 357 subtests in
  167.08s**.
