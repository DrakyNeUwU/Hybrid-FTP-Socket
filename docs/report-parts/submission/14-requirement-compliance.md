# 14. Requirement Traceability Matrix (Reference)

> **Chỉ dùng để mapping/reference, không dùng để claim trạng thái cuối.** Xem
> [`../../project-status.md`](../../project-status.md) cho tiến độ,
> [`../../requirement-checklist.md`](../../requirement-checklist.md) cho acceptance,
> và [`../../report.md`](../../report.md) cho bản nộp cuối.

**Owner:** A. **Reviewer:** B/C. **Source:** `../../requirement-checklist.md`,
đề gốc, `../../api-contract.md`, and final-week evidence.

### Role B — UDP data channel / RDT
- **Scope:** triển khai reliable transport trên UDP gồm header, checksum, ACK, retransmission, FIN/ABORT và recovery khi có packet loss/corruption.
- **Module chính:** `common/RDTHeader.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`.
- **Evidence:** chạy `python3 -m pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q` với kết quả `45 passed in 67.09s`.
- **Reference evidence:** RDT unit/fault evidence is linked below; B-F01
  technical wire-contract review is complete.

| Requirement của đề | Mức độ | Role | Report section | Code liên quan | Test/evidence | Reference coverage |
|---|---|---|---|---|---|---|
| TCP control, parser, replies, session | Basic/Advanced | A | 04 | `server/client_handler.py`, `command_parser.py`, `session.py`, `ftp_reply.py` | Role A audit 63 passed in 5.71s | Code and evidence mapped |
| 28 approved FTP commands (§2.2) | Basic/Advanced | A | 04 | `server/command_handler.py` | `TestCommandMatrix28RoleA`; full 199 passed | Code and evidence mapped |
| `MODE {S\|B\|C}` negotiation | Advanced | A | 04 | `command_handler.mode_cmd` | `TestModeComplianceRoleA`: S→200, B/C→502 | Limitation and evidence mapped |
| Reply codes chuẩn (§2.3) | General | A | 04 | `FTPReply` | 28-command matrix + TCP E2E | Code and evidence mapped |
| UDP payload với custom RDT | Excellent | B | 05 | `common/rdt_sender.py`, `rdt_receiver.py`, `RDTHeader.py` | `python3 -m pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q` → **45 passed in 67.09s** | Code and evidence mapped |
| Reliable transfer under loss/corruption | Excellent | B | 05 | `common/rdt_sender.py`, `common/rdt_receiver.py`, `tests/test_rdt_fault_injection.py` | Fault injection tests: packet loss, checksum corruption, ACK loss, cancel/abort recovery | Code and evidence mapped |
| Transfer lifecycle FIN/ABORT | Advanced/Excellent | B | 05 | `common/rdt_sender.py`, `common/rdt_receiver.py` | Protocol tests for FIN grace and abort cancellation | Code and evidence mapped |
| Binary integrity — SHA-256 | Advanced/Excellent | B/C | 05, 06, 10 | RDT + `FilesystemService` | FTP E2E 6 passed in 22.63s; `final-lan-*-sha256.txt` | Code and evidence mapped |
| Active and PASV | Advanced | A/B/C | 07 | `command_handler.py`, `common/rdt_utils.py` | E2E + two-machine LAN hashes | Code and evidence mapped |
| FTP-root/path/symlink security | Advanced | C/A | 06 | `filesystem_service.py`, `dir_manager.py` | traversal/symlink tests trong `tests/` | Code and evidence mapped |
| Atomic STOR, APPE lock, unique STOU | Advanced | C/A | 06, 08 | `filesystem_service.py`, `transfer_manager.py` | E2E 3 PASV clients + ABOR + disconnect | Code and evidence mapped |
| Multi-client isolated server | Advanced | C | 08 | `threaded_server.py`, `client_handler.py` | three PASV clients `1 passed in 5.34s` | Code and evidence mapped |
| CLI state/progress + safe logging | General | C | 09 | `client/cli_display.py`, server log | `week-2.5-cli-logging.log` | Code and evidence mapped |
| Unit, fault, integration tests | General/Excellent | C with A/B | 10 | `tests/` | full `199 passed in 96.72s` | Evidence mapped |
| Diagrams/structures 7 sections (§2.4) | Report | all | 03–08 | docs/report-parts | đủ section; diagram khớp code | Final assembly tracked in B-F02 |
| Task matrix, self/peer evaluation | Report | all | 11 | Git/docs | matrix có; percentage chờ sign-off | Final sign-off tracked in checklist |
| GenAI prompt/raw/refinement (§4.3) | Report | all | 13 | `docs/genai-log-*.md` | A/B/C logs đầy đủ | Source logs mapped |
| Demo logs/hash/client table (§4.5) | Submission | C | 10 | runtime artifacts | `docs/evidence/` gồm `final-lan-*` | Evidence mapped |

Các ô coverage chỉ nói rằng requirement đã có code hoặc artifact để tham chiếu.
Chúng không thay thế trạng thái cuối, sign-off, hay acceptance decision trong
`project-status.md` và `requirement-checklist.md`.
