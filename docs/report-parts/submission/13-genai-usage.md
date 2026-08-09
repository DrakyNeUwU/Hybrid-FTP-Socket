# 13. GenAI Usage and Refinement

**Trạng thái:** Provenance A/B/C được map tới các GenAI logs; final release
decision vẫn theo `docs/requirement-checklist.md`.
**Owner:** all. **Reviewer:** all.

Role A lưu exact prompt, raw-output summary, manual refinement, affected files
và evidence tại `../../genai-log-a.md`; Role C tương tự tại `../../genai-log-c.md`.
Log ghi rõ GenAI chỉ hỗ trợ phân tích, thiết kế và review; mọi thay đổi được
kiểm tra lại bằng code review và test thật.

| Hạng mục Role C | Manual refinement | Verification |
|---|---|---|
| Filesystem/concurrency | Giữ filesystem boundary, atomic cleanup và lock ownership rõ ràng | Filesystem/server/E2E tests |
| Go-Back-N/START | Chọn window 4, ACK tích lũy, retry bounded; không đổi header/TCP contract | RDT 27 pass; final full suite 199 pass |
| LAN ACTIVE | Chẩn đoán CP1252 và server-initiated UDP; thêm output-safe/probe behavior | CLI/E2E regression; ACTIVE LAN hash |
| Documentation migration | Đồng bộ evidence vào report parts, status/checklist và changelog | Link/evidence audit |

## Role B

Role B lưu prompt, raw-output summary, manual refinement và verification tại
`../../genai-log-b.md`. Log bao phủ audit/fix RDT, black-box protocol testing,
START inspection và final RDT contract/report verification. Mọi đề xuất được
đối chiếu lại với `RDTHeader`, sender/receiver, API contract và test thật.

| Hạng mục Role B | Manual refinement | Verification |
|---|---|---|
| RDT bug audit | Validate flags/length/checksum ACK, dùng socket do `TransferManager` cấp và sửa FIN grace | RDT/fault tests |
| Black-box protocol tests | Bổ sung transfer-ID và ABORT cases, không mock sai production behavior | `45 passed in 67.09s` |
| START/Go-Back-N review | Đối chiếu START ACK/retry, cumulative ACK/window 4 và FIN/ABORT với contract | Protocol 27 pass; full suite 199 pass |
| Final report support | Map RDT trace/evidence vào technical/05 và report tổng | `docs/evidence/final-week-rdt-gbn-verification.md` |

## Role A

Role A dùng GenAI cho toàn bộ vòng đời của `CommandHandler`, `ClientHandler`
và `TransferManager`: tách module, framing buffer TCP, tích hợp
`FilesystemService`, RDT adapters, chuẩn hoá reply code, anti-FTP bounce,
auth contract, validation chung và các task tuần cuối (MODE compliance,
28-command matrix). Mọi raw output đều được kiểm tra thủ công, sửa reply code,
xử lý edge case và xác nhận bằng unit test trước khi đưa vào production.

| Hạng mục Role A | Manual refinement | Verification |
|---|---|---|
| Refactor TCP Command Handler | Điều chỉnh cấu trúc thư mục, sửa `Session` constructor, bổ sung `FTPReply`, sửa lỗi import/indentation | Telnet thủ công từng command |
| TCP Framing Buffer | Buffer cộng dồn `\r\n`, bắt `UnicodeDecodeError` để không crash thread khi byte lỗi | Unit test split giữa hai `recv()` và nhiều command một `recv()` |
| Filesystem Integration | Giữ nguyên `FilesystemService` boundary, thêm `_FallbackFilesystem` cho test-only | 110 test pass, không regression |
| PASV/PORT/ABOR/Cleanup | Đóng socket cũ, validate PORT 6 số 0–255, resolve IP thật, reset `rename_from` toàn diện | `TestRenameFromReset`, PASV socket replacement test |
| RDT Adapters & TransferManager | Inject sender/receiver qua adapter, phân biệt `FilesystemOperationError`→550 và network→426 | `test_transfer_manager.py` pass, full suite 100% |
| Auth & Validation | Sửa auth contract (USER reset, PASS trước USER→503, anonymous), validation table chung | 14 test validation + 6 test auth, 61 test pass |
| Task A-F01 MODE compliance | MODE S→200, B/C→502 trung thực, X→501, chưa login→530 | `TestModeComplianceRoleA` 5 pass |
| Task A-F02 28-command matrix | Đủ 28 lệnh, HELP→214, lệnh ngoài đề SITE→502, luồng 150→226/4xx | Final audit 63 pass; full suite 199 pass |

Final report chỉ được nói GenAI-assisted ở mức có thể giải thích và truy vết
vào logs; không thay thế peer review, ownership hoặc verification độc lập.
