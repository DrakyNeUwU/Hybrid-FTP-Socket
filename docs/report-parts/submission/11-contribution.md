# 11. Contribution and Peer Evaluation

**Trạng thái:** Scope A và C đã ghi; phần trăm và sign-off chờ cả nhóm (B-F02/B-F03).
**Mục tiêu:** Map engineering components, commits and agreed percentages totaling 100%.
**Requirement:** RQ-10, RQ-11. **Owner:** A/C. **Reviewer:** all members.
**Nguồn:** `../../../planning/Socket Role.md`, Git history, role docs, evidence.

## 11.1 Task assignment matrix

| Module | Owner chính | Collaborators | Đóng góp / evidence |
|---|---|---|---|
| TCP control connection | A | C | buffer, CRLF framing, cleanup; command/audit tests |
| Command parser / dispatcher / FTP reply | A | — | 28-command matrix, reply codes; `TestCommandMatrix28RoleA` |
| Session management | A | C | per-client isolation, transfer ID; `tests/test_session.py` |
| Authentication | A | — | credential contract, RFC 959 reset; command tests |
| Transfer orchestration (`TransferManager`) | A | B, C | `150 → 226/4xx`, ABOR/cancel; transfer-manager tests |
| UDP reliable transfer (RDT) | B | A | Go-Back-N window 4, START ACK/retry; final RDT verification |
| Filesystem boundary | C | A | FTP-root validation, binary I/O, atomic `.part`, APPE lock, STOU; filesystem/transfer tests |
| Server concurrency | C | A | thread-per-client, active-session registry, safe stop; threaded/E2E tests |
| Integration | C | A | `TransferContext` handoff, cleanup mapping, Active/PASV E2E; transfer manager và E2E logs |
| Demo/evidence | C | A | LAN PASV/ACTIVE, SHA-256, progress/logging; `docs/evidence/final-*` |
| Report support | C | A | technical drafts 01/03/06/08/09, testing evidence; report-parts workspace |
| Report parts 02/04/07/14 | A | B/C | requirement mapping, control channel, Active/PASV, compliance; report-parts workspace |

## 11.2 Commit history đại diện (Role A)

- `66979e1` [role-a] complete tasks A-F01 and A-F02 with mode compliance tests and section 4 report
- `efcea63` [docs][role-a] add week 2.5 detailed changes to report and genai log
- `7571eb6` [docs][role-a] fill report-parts owned by role a with final-week evidence
- `bc80b9c` docs: add final LAN evidence logs, screenshots, and test binaries (evidence chung)

## 11.3 Self / peer evaluation

- **Role A (self):** hoàn thành TCP control, 28-command compliance matrix, MODE
  negotiation trung thực (B/C → 502), transfer lifecycle `150 → 226/4xx`,
  anti-FTP bounce, session isolation; xem `../../report_role_a_week2.md` §5/§9.
- **Role C (self):** filesystem boundary, concurrency, integration, Go-Back-N
  window 4, LAN evidence; xem `docs/role-c-week-2.md`.
- **Peer review:** A review phần mode/command của B-F01; C review integration
  transfer; B review traceability matrix (A-F02). Kết quả audit: Role A `63 passed
  in 5.71s`, Role C `135 passed in 86.22s`.

## 11.4 Percentages

**TODO(A/C/B):** Peer evaluation percentage phải do A/B/C cùng chốt, tổng đúng
100%, gắn commit hash/review record và sign-off. Không suy đoán percentage chỉ từ
số file hoặc số test; chốt sau khi B tổng hợp report (B-F02) và oral dry run
(B-F03).

**DoD:** Matrix phủ mọi component và tổng percentage đúng 100%.
