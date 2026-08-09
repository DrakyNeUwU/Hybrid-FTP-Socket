# 14. Requirement Compliance Matrix (Historical Draft)

> **Snapshot cập nhật 09/08/2026 — không phải trạng thái hiện tại.** Xem
> [`../../project-status.md`](../../project-status.md) cho tiến độ,
> [`../../requirement-checklist.md`](../../requirement-checklist.md) cho acceptance,
> và [`../../report.md`](../../report.md) cho bản nộp cuối.

**Trạng thái snapshot:** cập nhật theo code tuần cuối; Role A sign-off phần control/command.
**Owner:** A. **Reviewer:** B/C. **Source:** `../../requirement-checklist.md`, đề gốc, `../../api-contract.md`, `../../report_role_a_week2.md`.

### Role B — UDP data channel / RDT
- **Scope:** triển khai reliable transport trên UDP gồm header, checksum, ACK, retransmission, FIN/ABORT và recovery khi có packet loss/corruption.
- **Module chính:** `common/RDTHeader.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`.
- **Evidence:** chạy `pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q` với kết quả `45 passed in 70.66s`.
- **Status:** Verified.

| Requirement của đề | Mức độ | Role | Report section | Code liên quan | Test/evidence | Trạng thái |
|---|---|---|---|---|---|---|
| TCP control, parser, replies, session | Basic/Advanced | A | 04 | `server/client_handler.py`, `command_parser.py`, `session.py`, `ftp_reply.py` | Role A audit 63 passed in 5.71s | Verified |
| 28 approved FTP commands (§2.2) | Basic/Advanced | A | 04 | `server/command_handler.py` | `TestCommandMatrix28RoleA`; full 199 passed | Verified |
| `MODE {S\|B\|C}` negotiation | Advanced | A | 04 | `command_handler.mode_cmd` | `TestModeComplianceRoleA`: S→200, B/C→502 | Verified (B/C limitation ghi rõ) |
| Reply codes chuẩn (§2.3) | General | A | 04 | `FTPReply` | 28-command matrix + TCP E2E | Verified |
| UDP payload với custom RDT | Excellent | B | 05 | `common/rdt_sender.py`, `rdt_receiver.py`, `RDTHeader.py` | `tests/test_rdt.py` 27 passed; fault injection | Verified |
| Binary integrity — SHA-256 | Advanced/Excellent | B/C | 05, 06, 10 | RDT + `FilesystemService` | FTP E2E 6 passed in 22.63s; `final-lan-*-sha256.txt` | Verified |
| Active and PASV | Advanced | A/B/C | 07 | `command_handler.py`, `common/rdt_utils.py` | E2E + two-machine LAN hashes | Verified |
| FTP-root/path/symlink security | Advanced | C/A | 06 | `filesystem_service.py`, `dir_manager.py` | traversal/symlink tests trong `tests/` | Verified |
| Atomic STOR, APPE lock, unique STOU | Advanced | C/A | 06, 08 | `filesystem_service.py`, `transfer_manager.py` | E2E 3 PASV clients + ABOR + disconnect | Verified |
| Multi-client isolated server | Advanced | C | 08 | `threaded_server.py`, `client_handler.py` | three PASV clients `1 passed in 5.34s` | Verified |
| CLI state/progress + safe logging | General | C | 09 | `client/cli_display.py`, server log | `week-2.5-cli-logging.log` | Verified |
| Unit, fault, integration tests | General/Excellent | C with A/B | 10 | `tests/` | full `199 passed in 96.72s` | Verified |
| Diagrams/structures 7 sections (§2.4) | Report | all | 03–08 | docs/report-parts | đủ section; diagram khớp code | In progress (B-F02) |
| Task matrix, self/peer evaluation | Report | all | 11 | Git/docs | matrix có; percentage chờ sign-off | In progress |
| GenAI prompt/raw/refinement (§4.3) | Report | all | 13 | `docs/genai-log-*.md` | A/B/C logs đầy đủ | Verified |
| Demo screenshots/logs/hash/client table (§4.5) | Submission | C | 10 | runtime artifacts | `docs/evidence/` gồm `final-lan-*` | Verified |

`Verified` được gán cho hàng có artifact thật (test log/hash/screenshot). Các hàng
còn "In progress" thuộc phần B-F02 (tổng hợp report) và B-F03 (oral/live-code),
không phải defect kỹ thuật.
