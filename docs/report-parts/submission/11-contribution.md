# 11. Contribution and Peer Evaluation

**Trạng thái:** Role C scope đã ghi; phần trăm và sign-off chờ cả nhóm.
**Owner:** A/C. **Reviewer:** all members.
**Nguồn:** `../../../planning/Socket Role.md`, Git history, role docs, evidence.
| Thành phần | Owner chính | Đóng góp Role C | Evidence |
|---|---|---|---|
| Filesystem boundary | C | FTP-root validation, binary I/O, metadata, atomic `.part`, APPE lock, STOU | filesystem/transfer tests |
| Server concurrency | C | Thread-per-client, active-session registry, safe stop/unregister | threaded/E2E tests |
| Integration | C | `TransferContext` handoff, cleanup mapping, Active/PASV E2E | transfer manager và E2E logs |
| Reliability extension | C, B review | Go-Back-N window 4, START ACK/retry, bounded retransmission | final RDT verification |
| Demo/evidence | C | LAN PASV/ACTIVE, SHA-256, progress/logging evidence | `docs/evidence/final-*` |
| Report support | C | Technical drafts 01/03/06/08/09 và testing evidence | report-parts workspace |

Peer evaluation percentage phải do A/B/C cùng chốt, tổng đúng 100%, gắn commit
hash/review record và sign-off. Không suy đoán percentage chỉ từ số file hoặc
số test.
**Trạng thái:** Hoàn thành một phần  
**Mục tiêu:** Map engineering components, commits and agreed percentages totaling 100%.  
**Requirement:** RQ-10, RQ-11. **Owner:** A/C. **Reviewer:** all members.  
**Source:** `../../../planning/Socket Role.md`, Git history, role docs.  
**Code:** commit history and owned modules.

## 11.1 Task assignment matrix

| Module | Owner | Collaborators |
|---|---|---|
| TCP control connection | A | C |
| Command parser / dispatcher | A | — |
| FTP reply management | A | — |
| Session management | A | C |
| Authentication | A | — |
| Transfer orchestration (`TransferManager`) | A | B, C |
| UDP reliable transfer (RDT) | B | A |
| Filesystem security (`FilesystemService`) | C | A |
| Thread management / concurrency | C | A |
| CLI progress + logging | C | A |

## 11.2 Commit history đại diện (Role A)

- `66979e1` [role-a] complete tasks A-F01 and A-F02 with mode compliance tests and section 4 report
- `efcea63` [docs][role-a] add week 2.5 detailed changes to report and genai log
- `bc80b9c` docs: add final LAN evidence logs, screenshots, and test binaries (evidence chung)

## 11.3 Self / peer evaluation

- **Role A (self):** hoàn thành TCP control, 28-command compliance matrix, MODE
  negotiation trung thực, transfer lifecycle `150 → 226/4xx`, anti-FTP bounce,
  session isolation; xem `../../report_role_a_week2.md` §5.
- **Peer review:** A review phần mode/command của B-F01; C review integration
  transfer; B review traceability matrix (A-F02). Kết quả audit: Role A `63 passed
  in 5.71s`, Role C `135 passed in 86.22s`.

## 11.4 Percentages

**TODO(A/C):** Chốt percentage contribution tổng đúng 100% sau khi B tổng hợp
report (B-F02) và có sign-off cả nhóm (B-F03); không suy luận từ self-assessment.

**DoD:** Matrix phủ mọi component và tổng percentage đúng 100%.
