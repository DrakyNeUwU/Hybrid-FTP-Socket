# 9. Client, CLI and Logging

**Trạng thái:** Hoàn thành phần Role C; chờ reviewer chọn artifact để đưa vào report.
**Owner:** C. **Reviewer:** A.
**Nguồn:** `client/cli_display.py`, `client/demo_transfer.py`, `server/logging_utils.py`.

CLI nhận callback progress trực tiếp từ RDT cho upload/download. `TransferContext`
truyền total bytes đã validate cho RETR START, vì vậy download hiển thị tổng thực
0→100% thay vì coi từng chunk là hoàn thành. Output có fallback encoding-safe để
không crash trên Windows CP1252.

Server log theo lifecycle: client IP, command đã redact `PASS`, FTP reply,
session ID, transfer ID, mode, byte count, outcome và active-session snapshot.
Các dữ kiện hiển thị/logged đều đến từ live transfer state; không log credential.

ACTIVE LAN được tăng tính ổn định bằng zero-payload UDP START probe trước RETR
và sau reply `150`; thay đổi này không đổi TCP command/reply hay RDT header.

| Evidence | Kết quả |
|---|---|
| CLI + E2E regression | 13 passed in 23.09s sau CP1252/ACTIVE diagnosis |
| ACTIVE probe regression | 1 passed in 5.47s |
| LAN logs | Progress và success cho PASV/ACTIVE ở `../../evidence/final-lan-*.log` |
| Screenshot | PASV progress/server/success ở `../../evidence/screenshots/` |

**DoD:** PASS luôn redact; progress dùng total thật; log cho phép examiner lần
theo session/transfer nhưng không để lộ credential.
