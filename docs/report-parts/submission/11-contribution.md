# 11. Contribution and Peer Evaluation

**Trạng thái:** Scope kỹ thuật đã ghi; percentage và sign-off cuối chờ cả nhóm.
**Owner:** A/C. **Reviewer:** all members.
**Nguồn:** `../../../planning/Socket Role.md`, Git history, report-parts và evidence final-week.

## 11.1 Task assignment matrix

| Component | Owner | Collaborators | Evidence / deliverable |
|---|---|---|---|
| TCP control, parser, replies, authentication | A | C review | 28-command matrix; Role A audit 63 passed |
| Session and transfer orchestration | A | B/C | Per-client isolation, `150 → 226/4xx`, ABOR lifecycle |
| Active/PASV negotiation | A/B | C | PORT/PASV contract, LAN PASV/ACTIVE hashes |
| UDP RDT | B | A/C review | Header, checksum, ACK/retry, FIN/ABORT, Go-Back-N |
| Filesystem boundary | C | A | FTP-root safety, atomic `.part`, APPE lock, STOU |
| Server concurrency and integration | C | A/B | Thread-per-client, session registry, cleanup, E2E |
| CLI/logging and demo evidence | C | A | Progress, PASS redaction, LAN logs/hashes |
| Final report integration | B | A/C sign-off | `docs/report.md`, report-parts, evidence index |

## 11.2 Role summaries

- **Role A:** TCP control channel, command parser/dispatcher, session/authentication,
  FTP replies, 28-command compliance, MODE handling, PORT/PASV control lifecycle
  and transfer orchestration.
- **Role B:** RDT header and UDP sender/receiver, checksum, ACK/retry,
  START/FIN/ABORT lifecycle, fault-injection testing and final report integration.
- **Role C:** Filesystem sandbox and atomic lifecycle, thread/session management,
  transfer integration, Go-Back-N window 4, CLI/logging, LAN demo and final
  evidence collection.

## 11.3 Evidence and peer review

- Role A control/session audit: **63 passed in 5.71s**.
- Role B RDT/fault tests: **45 passed in 67.09s**; final contract evidence is in
  `../technical/05-data-channel-rdt.md` and `../../evidence/final-week-rdt-gbn-verification.md`.
- Role C focused audit: **135 passed in 86.22s**; final full regression:
  **199 passed in 96.72s**; LAN evidence is in `../../evidence/final-lan-*`.
- A reviews command/mode behavior; B reviews RDT contract/report traceability;
  C reviews integration, cleanup and evidence selection.

## 11.4 Percentages and sign-off

**TODO(A/B/C):** Agree contribution percentages totaling exactly 100% after
Role B completes `docs/report.md` and the team completes the oral dry run.
Record each member's sign-off with the final report/release checklist. Do not
infer percentages from file count or self-assessment alone.

| Final decision | Required record | Current state |
|---|---|---|
| Contribution percentage | A/B/C percentage, total exactly 100%, and decision date | Pending group decision |
| Technical sign-off | A review for control/command; C review for filesystem/concurrency/evidence | Pending release-checklist record |
| Submission sign-off | All members confirm report claims, oral dry run and clean Git release | Pending after the two rows above |

The authoritative gate is `docs/requirement-checklist.md`; this component only
records the final decision after that checklist has supporting evidence.
