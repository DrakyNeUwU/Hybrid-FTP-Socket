# Code Change History — Hybrid FTP

Tài liệu này ghi lại các thay đổi theo tuần để dùng làm minh chứng tiến độ.
Các trạng thái chỉ dựa trên code/test đã có, không thay thế demo end-to-end.

## Tuần 1 — Nền tảng và phân chia module

| Role | Công việc | Kết quả |
|---|---|---|
| A | Tách TCP server, command parser, command handler và session | Có cấu trúc xử lý command theo từng client |
| B | Tạo RDT header, sender/receiver cơ bản | Có sequence, ACK, checksum và FIN |
| C | Xây filesystem helper/service và FTP root | Có xử lý file binary và path cơ bản |

## Tuần 2 — Chức năng chính

| Role | Công việc | Kết quả |
|---|---|---|
| A | Bổ sung USER/PASS, directory command, PORT/PASV, RETR/STOR và reply | TCP command matrix được mở rộng |
| B | Bổ sung retransmission, duplicate và checksum handling | RDT có stop-and-wait cơ bản |
| C | Bổ sung root confinement, atomic upload và metadata | Filesystem không ghi trực tiếp ngoài FTP root |

## Tuần 2.5 — Audit và sửa lỗi tích hợp

| Role | Vấn đề phát hiện | Thay đổi đã thực hiện | Bằng chứng |
|---|---|---|---|
| A | Transfer chồng nhau ghi đè session state | Thêm guard trả `450 Transfer already in progress` | Test Role A pass |
| A/B | `TransferManager` truyền Event nhưng adapter cần context | Thêm `common/rdt_context.py` và truyền `TransferContext` | Adapter clean transfer pass |
| B | Server còn dùng adapter RDT cũ | `server/rdt_adapter.py` chuyển thành compatibility export | Import dùng cùng implementation |
| B | Header/ACK chưa kiểm tra chặt | Validate flags, length, checksum, peer, transfer ID và ACK sequence | Header/protocol 21/21 pass |
| B | Out-of-order test làm crash do log Unicode | Đổi log runtime sang ASCII | Protocol test pass |
| B | Receiver chờ vô hạn khi sender mất | Giới hạn receiver timeout mặc định | Max-retry test pass |
| C | Filesystem lifecycle cần giữ nguyên khi RDT fail/cancel | Giữ `FilesystemService` làm nơi commit và cleanup | Transfer manager tests |
| C | Cần evidence demo thật cho tích hợp | Chạy Active upload + download bằng `client.demo_transfer` | Client nhận 220 và `Success: ACTIVE upload + download` |
| C | Cần xác nhận hai data modes | Chạy PASV demo thủ công sau Active | Người chạy demo xác nhận PASV pass; giữ hash/video để nộp |
| C | Cần evidence integrity cho hai mode | Lưu SHA-256 source/server/download cho Active và PASV | Hai file trong `docs/evidence/` có ba hash trùng khớp mỗi mode |
| A/C | Full suite WSL2 có 3 test fail | Sửa TCP/IP address fallback và thay test debug ECHO bằng FTP `NOOP` | `python3 -m pytest -q`: 186 passed in 104.09s; log lưu trong `docs/evidence/` |
| C | Chưa có bằng chứng transfer đa client | Thêm test 3 client PASV đồng thời, download directory riêng cho mỗi client và kiểm tra hash source/server/client | Test riêng: 1 passed in 5.34s; toàn bộ E2E: 3 passed in 15.47s; logs `docs/evidence/week-2.5-three-client.log`, `week-2.5-e2e-transfer.log` |
| C | ABOR/disconnect chưa được chứng minh giữa transfer | Map `RuntimeError` từ RDT sang `TransferResult(426)`; thêm PASV upload chờ UDP rồi ABOR/disconnect, kiểm tra `.part`, file cũ và session registry | E2E: 5 passed in 18.03s; full WSL2: 189 passed in 113.94s; `docs/evidence/week-2.5-*.log` |
| C | Server chỉ có entry point localhost, PASV LAN có thể quảng bá sai IP | Thêm `--host`, `--port`, `--ftp-root`, `--advertise-host`; session ưu tiên địa chỉ quảng bá cấu hình | `python3 -m server.threaded_server --help`; threaded + E2E: 10 passed in 21.56s |
| C | `tuan-2.5-fix.md` trộn audit cũ với trạng thái mới, tạo checklist mâu thuẫn | Viết lại thành checklist hiện tại theo Role A/B/C, dependency, DoD và evidence links | Review đối chiếu full pytest 189 passed, E2E 5 passed và các evidence đã lưu |
| A/B/C | LIST/NLST bị để thành dependency dù đề chỉ yêu cầu command/reply TCP | Đối chiếu đề §1.1–1.2, §2.2–2.3 và chốt listing là TCP textual result; UDP chỉ mang file payload | `docs/api-contract.md` §6.1; command tests và full pytest 189 passed |
| C | CLI progress chỉ là UI helper; server chưa có lifecycle log đủ để demo | Nối RDT progress vào `FTPClient`/demo; log IP, command redact, reply, session/transfer, table, mode/bytes/result | 62 focused tests passed in 22.16s; full pytest 189 passed in 102.50s |
| C | Download progress coi mỗi chunk là 100% vì RETR sender không biết tổng file size | Thêm `TransferContext.total_bytes`; TransferManager lấy size đã validate và sender đưa vào RDT START | E2E 5 passed in 17.61s; full pytest 189 passed in 106.91s |
| C | Cần evidence trực quan cho progress/server observability | Người chạy demo PASV lưu screenshot server log, progress 0→100% và success dưới `docs/evidence/screenshots/` | User confirmation 08/08/2026; text logs/hash đã lưu trong `docs/evidence/` |

## Trạng thái kiểm chứng hiện tại — 08/08/2026

- Role A regression: **52 tests pass**.
- RDT header/protocol logic: **21 tests pass**.
- RDT fault injection + adapter fault injection: **14 tests pass**.
- Localhost TCP + UDP/RDT integration: **2 tests pass** (Active/PASV upload,
  download, and SHA-256 comparison).
- Tổng các nhóm đã chạy: **87 test pass**; một số test có cảnh báo resource
  từ test cũ nhưng không fail.
- Full pytest trên WSL2/Linux: **189 passed in 113.94s**; log đã lưu trong
  `docs/evidence/week-2.5-pytest.log`.
- Active/PASV localhost đã có test và demo; 3 client PASV đồng thời,
  ABOR/disconnect đang chờ UDP đã có evidence end-to-end. Demo khác máy vẫn
  chưa có bằng chứng.

## Cách dùng làm minh chứng

Khi nộp báo cáo, đính kèm:

1. File này để chứng minh lịch sử thay đổi.
2. `docs/project-status.md` để chứng minh trạng thái hiện tại.
3. `docs/api-contract.md` để chứng minh contract A–B–C.
4. Output các lệnh test ở phần hướng dẫn chạy trong câu trả lời bàn giao.

Không ghi “hoàn thành toàn bộ” cho Active/PASV hoặc FTP end-to-end nếu chưa có
log client/server và hash nguồn/đích.

## 09/08/2026 — Final-week documentation source-of-truth consolidation

| Role owner | Problem | Files changed | Reason | Verification evidence |
|---|---|---|---|---|
| C (documentation integration) | Nhiều file trạng thái/report cũ mâu thuẫn với full regression và FTP E2E đã có | `README.md`, `docs/project-status.md`, `docs/requirement-checklist.md`, `planning/`, `docs/report-parts/`, tài liệu tuần và final-week plan | Chỉ định một status hiện hành và một checklist acceptance; tổ chức planning thành requirement/ownership, status navigation và weekly plans; tổ chức report drafts thành technical/submission; cập nhật README theo commands và tài liệu hiện tại. `docs/report.md` được để nguyên cho Role B hoàn thiện. | Đối chiếu `189 passed in 106.91s`, FTP E2E `5 passed in 18.03s`, hash Active/PASV; kiểm tra Git và tìm stale claims trong tài liệu hiện hành |

## 09/08/2026 — Role C Go-Back-N Excellent RDT lifecycle

| Role owner | Problem | Files changed | Reason | Verification evidence |
|---|---|---|---|---|
| C, with B wire-contract review pending | Sender was Stop-and-Wait and START metadata had no ACK/retry | `common/rdt_context.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`, `tests/test_rdt.py`, Role C/status/contract docs | Implement bounded, streaming-safe Go-Back-N window 4, cumulative ACK, finite START retry and maintain atomic cleanup without changing header or TCP command interfaces | WSL2: final focused 50 passed in 85.01s; full suite 192 passed in 93.06s; `docs/evidence/final-week-rdt-gbn-verification.md` |
| C | Windows CP1252 output crashed during ACTIVE progress; server-initiated ACTIVE RETR UDP traffic could be blocked until the client created state | `client/demo_transfer.py`, `client/ftp_client.py`, `tests/test_cli_display.py`, evidence/status docs | Make progress output encoding-safe and send zero-payload START probes before `RETR` and after `150`, without changing TCP or RDT header contracts | WSL2 full regression: 199 passed in 96.72s; physical LAN PASV and ACTIVE upload/download both succeeded with matching source/server/client SHA-256 |

## 09/08/2026 — Role C report-component migration

| Role owner | Problem | Files changed | Reason | Verification evidence |
|---|---|---|---|---|
| C | Week 2 Role C document duplicated integration/evidence material needed by report components | `docs/report-parts/technical/01,03,06,08,09`, `docs/report-parts/submission/10–13`, checklist/status/contract docs; removed `docs/role-c-week-2.md` | Move ownership-scoped technical narrative and final evidence into the report workspace; preserve one evidence-backed source per report component | Cross-check against final verification: 199 full tests, 6 expanded E2E, LAN PASV/ACTIVE SHA-256 artifacts; link and diff audit pending handoff |

## 09/08/2026 — Remove role-week-2 sources and repair report references

| Role owner | Problem | Files changed | Reason | Verification evidence |
|---|---|---|---|---|
| A/B/C documentation | Role A/B/C Week 2 documents were intentionally removed, leaving report-part source links broken; contribution matrix also duplicated merge content | Report parts 02, 04, 05, 07, 11 and 14 | Use surviving requirement, API contract and evidence files as canonical sources; make LIST/NLST documentation match the TCP-only contract; consolidate contribution ownership | Reference search and `git diff --check` run after the edit |

## 09/08/2026 — Final-week plan aligned to the report workspace

| Role owner | Problem | Files changed | Reason | Verification evidence |
|---|---|---|---|---|
| C (documentation integration) | Final-week actions still named deleted Role Week 2 files and did not distinguish the requirement-mapping draft from the current project status | `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md` | Point B/C work to the report-parts workspace; define `submission/14` as mapping/reference only, with final claims sourced from project status and the acceptance checklist | Manual path/reference review; `git diff --check` passed |
