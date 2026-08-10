# Requirement Acceptance Checklist — Hybrid FTP

**Audit date:** 10/08/2026
**Requirement source:** `planning/reference/Project1_SocketProgramming_2026.md`
**Current status source:** `docs/project-status.md`

| Requirement / acceptance gate | Status | Owner | Evidence |
|---|---|---|---|
| TCP control, replies, authentication, MODE S/B/C, and session isolation | In progress | A | Final-fix code reverted for A handoff; B/C semantics, strict auth and client framing pending |
| Commands, filesystem routing, and FTP-root safety | In progress | A/C | C filesystem scope verified; A command compliance re-verification pending |
| UDP/RDT ACK, retry, checksum, FIN, and Go-Back-N | Done | B/C | Protocol and fault tests |
| Active/PASV upload and download | Done | A/B/C | Localhost and LAN SHA-256 evidence; current post-handoff regression passes |
| Multi-client isolation, ABOR, and disconnect cleanup | Done | C | Shared-service, same-file APPE and FTP E2E evidence |
| CLI progress and redacted server logging | Done | C | CLI and LAN logs |
| Final report, contribution matrix, peer assessment, GenAI logs | In progress | B | Team contribution and release decision pending |
| Oral preparation and Git release hygiene | In progress | B | Clean release check pending |

Every completed row must cite real evidence. Do not mark an item complete from
source inspection alone.
