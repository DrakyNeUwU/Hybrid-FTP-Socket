# 2. Requirement Analysis

**Trạng thái:** Hoàn thành (snapshot tuần cuối, 09/08/2026)  
**Mục tiêu:** Trình bày checklist chính thức và mapping owner.  
**Requirement:** toàn bộ yêu cầu đề §1–§4.5. **Owner:** A. **Reviewer:** B/C.  
**Source:** [`../../requirement-checklist.md`](../../requirement-checklist.md), đề gốc §2.1–§2.4, [`../../report_role_a_week2.md`](../../report_role_a_week2.md).  
**Code:** toàn repo theo matrix.

## 2.1 Requirement → Owner mapping

| Requirement (mục đề) | Mức độ | Owner | Code | Test / evidence |
|---|---|---|---|---|
| TCP control channel, session isolation, reply codes | Basic/Advanced | A | `server/client_handler.py`, `server/command_parser.py`, `server/session.py`, `server/ftp_reply.py` | Role A audit **63 passed in 5.71s**; full regression **199 passed in 96.72s** |
| 28 approved commands (§2.2) parse/validate/reply | Basic/Advanced | A | `server/command_handler.py` | `TestCommandMatrix28RoleA`; reply matrix `04-control-channel.md` §4.2 |
| `TYPE` / `MODE` negotiation (§2.2) | Advanced | A | `command_handler.type_cmd` / `mode_cmd` | `TestModeComplianceRoleA`: MODE S→200, B/C→502, X→501, chưa login→530 |
| Reply codes ba chữ số chuẩn (§2.3) | General | A | `FTPReply` | 28-command matrix + TCP E2E |
| UDP payload qua custom RDT (§1.2) | Excellent | B | `common/rdt_sender.py`, `rdt_receiver.py`, `RDTHeader.py` | `tests/test_rdt.py` **27 passed**; fault-injection suite |
| Binary integrity — SHA-256 | Advanced/Excellent | B/C | RDT + `FilesystemService` | FTP E2E **6 passed in 22.63s**; `docs/evidence/final-lan-*-sha256.txt` |
| Active/PASV negotiation | Advanced | A/B | `command_handler.port_cmd` / `pasv`, `common/rdt_utils.py` | FTP E2E + LAN hai máy (`07-active-pasv.md`) |
| FTP-root/path/symlink security | Advanced | C/A | `common/filesystem_service.py`, `common/dir_manager.py` | security tests trong `tests/` |
| Atomic STOR/APPE, unique STOU, locks | Advanced | C/A | `FilesystemService`, `TransferManager` | E2E 3 PASV clients, ABOR, disconnect |
| Multi-client isolated server | Advanced | C | `server/threaded_server.py`, `client_handler.py` | three PASV clients; shutdown test |
| CLI state/progress + logging redaction | General | C | `client/cli_display.py`, server log | `docs/evidence/week-2.5-cli-logging.log` |
| Report 7 sections, task matrix, peer eval, GenAI log | Report | all | docs | `docs/report.md`, `docs/genai-log-*.md` |

## 2.2 Chú thích

- Trạng thái hiện tại duy nhất: [`../../project-status.md`](../../project-status.md); acceptance trước nộp: [`../../requirement-checklist.md`](../../requirement-checklist.md).
- Role A hoàn thành **A-F01** (MODE compliance) và **A-F02** (28-command matrix) trong tuần cuối; mọi claim có evidence tại `docs/evidence/final-week-rdt-gbn-verification.md`.
- `MODE B/C` được báo cáo trung thực là limitation (`502`) vì bảng §2.2 không yêu cầu codec block/compressed ở data path — không claim success giả.
- `Verified` chỉ gán cho hàng có artifact thật (log/hash/screenshot). Các hàng report/oral còn "In progress" thuộc B-F02/B-F03, không phải defect kỹ thuật.

**DoD:** Mọi requirement có ID (§ đề), owner, section report, code/test/evidence hoặc TODO rõ ràng.
