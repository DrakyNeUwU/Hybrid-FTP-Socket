# Requirement Acceptance Checklist — Hybrid FTP

**Audit date:** 09/08/2026
**Requirement source:** `planning/reference/Project1_SocketProgramming_2026.md`
**Current status source:** `docs/project-status.md`

| Requirement / acceptance gate | Status | Owner | Evidence |
|---|---|---|---|
| TCP control, replies, authentication, and session isolation | Done | A | Final WSL2 regression: 199 passed |
| Commands, filesystem routing, and FTP-root safety | Done | A/C | Focused audit and final regression |
| UDP/RDT ACK, retry, checksum, FIN, and Go-Back-N | Done | B/C | Protocol and fault tests |
| Active/PASV upload and download | Done | A/B/C | Localhost and LAN SHA-256 evidence |
| Multi-client isolation, ABOR, and disconnect cleanup | Done | C | FTP E2E logs |
| CLI progress and redacted server logging | Done | C | CLI and LAN logs |
| Final report, contribution matrix, peer assessment, GenAI logs | In progress | B | Team contribution and release decision pending |
| Oral preparation and Git release hygiene | In progress | B | Clean release check pending |

Every completed row must cite real evidence. Do not mark an item complete from
source inspection alone.
