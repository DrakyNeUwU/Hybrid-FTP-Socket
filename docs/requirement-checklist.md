# Requirement Acceptance Checklist — Hybrid FTP

**Audit date:** 09/08/2026
**Requirement source:** `planning/reference/Project1_SocketProgramming_2026.md`
**Current status:** pre-submission acceptance checklist; `docs/project-status.md` is the sole operational status source.

| Requirement / acceptance gate | Trạng thái | Owner cuối | Evidence |
|---|---|---|---|
| TCP control, FTP replies, authentication, and session isolation | Done | A | Final WSL2 regression: `199 passed in 96.72s`; `docs/evidence/final-week-rdt-gbn-verification.md` |
| Commands, filesystem routing, and FTP-root safety | Done | A/C | Focused C audit: `135 passed in 86.22s`; final regression `199 passed` |
| UDP payload through custom RDT, ACK/retry/checksum/FIN | Done | B/C | Go-Back-N window 4, START ACK/retry; protocol 27 pass; final suite 199 pass |
| Sliding-window flow control (Excellent) | Done | C/B | `tests/test_rdt.py` proves four in-flight packets and START ACK retry |
| Active/PASV upload/download localhost | Done | A/B/C | Expanded E2E: `6 passed in 22.63s`; final verification artifact |
| Binary integrity source/server/client | Done | B/C | Localhost and LAN SHA-256 logs under `docs/evidence/final-lan-*-sha256.txt` |
| Multi-client isolation, ABOR/disconnect cleanup | Done | C | FTP E2E log: three PASV clients, ABOR, disconnect |
| CLI progress và server logging có redaction | Done | C | `docs/evidence/week-2.5-cli-logging.log`, LAN server/client logs |
| Active/PASV trên hai máy LAN | Done | C | PASV/ACTIVE two-machine upload/download; source/server/client SHA-256 match |
| Required final report, task matrix, peer assessment, GenAI log | In progress | B | Report technical audit passed; contribution percentage and Git release are pending |
| Oral preparation and Git release hygiene | In progress | B | Oral pack/locator is ready; Git release check is pending |

## Pre-submission gates

### 1. Report claim review

- [x] Technical audit confirms that `docs/report.md` has no claims contrary to evidence; A's TCP/commands and C's filesystem/concurrency/LAN work were compared.
- [x] Every `Done` row has an accessible command, log, or hash; no new screenshot is needed because logs/hashes are valid evidence.
- [x] LAN/Go-Back-N evidence was reviewed and embedded/referenced in the report.

### 2. Contribution percentage and sign-off

- [ ] A/B/C must finalize percentages totaling 100%, the decision date, and sign-off in `docs/report-parts/submission/11-contribution.md`.

### 3. Oral preparation and Git release hygiene

- [x] A 20-question oral pack and code/evidence locators are in the final-week plan; a dry run is not an internal gate.
- [ ] `git status --short --branch --untracked-files=all` is clean, with no runtime transfer data except intentionally saved evidence.
- [x] Full regression rerun: `python3 -m pytest -q` — 199 passed in 96.72s; evidence `docs/evidence/final-week-rdt-gbn-verification.md`.
