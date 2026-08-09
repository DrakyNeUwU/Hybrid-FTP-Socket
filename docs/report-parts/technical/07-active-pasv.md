# 7. Active and PASV Modes

**Trạng thái:** Hoàn thành  
**Mục tiêu:** Chốt UDP endpoint negotiation and lifecycle.  
**Requirement:** RQ-02, RQ-05, RQ-10. **Owner:** A/B. **Reviewer:** C.  
**Source:** `../../api-contract.md`, `../../requirement-checklist.md`, and
`../../evidence/final-lan-pasv-sha256.txt` / `final-lan-active-sha256.txt`.
**Code:** `server/command_handler.py`, `common/rdt_utils.py`.

## 7.1 PORT — Active Mode (Role A)

- Format `PORT h1,h2,h3,h4,p1,p2`; parse đủ 6 số, mỗi số trong `0..255`, port `> 0` và `≤ 65535`; non-numeric → `501 Syntax error in parameters`.
- **Anti-FTP bounce:** IP trong lệnh PORT phải khớp IP TCP peer của client (allowlist loopback `127.x.x.x`); không khớp → `504 Command not implemented for that parameter`.
- Lưu `session.data_host`, `session.data_port`, `session.data_mode = "ACTIVE"` → `200 PORT command successful`.

## 7.2 PASV — Passive Mode (Role A)

- Đóng `session.data_socket` cũ trước khi tạo socket UDP mới (không rò rỉ file descriptor), đặt `data_socket = None` ngay sau close.
- Resolve IP server thật bằng `socket.gethostbyname(socket.gethostname())`; fallback `127.0.0.1`; khi server bind `0.0.0.0`, dùng `advertised_host` nếu được cấu hình (launcher LAN).
- Trả `227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)` với IP thật.

## 7.3 Cleanup và lifecycle

- Chuyển PORT→PASV hoặc PASV→PORT thay thế endpoint cũ; `QUIT`/disconnect/shutdown reset toàn bộ data state trong `ClientHandler.cleanup()`.
- Transfer command (`RETR`/`STOR`/`STOU`/`APPE`) chỉ gửi `150` khi có endpoint hợp lệ; thiếu → `425 Use PORT or PASV first`.
- Endpoint do Role A quản lý trên TCP control; payload file đi UDP/RDT, `LIST`/`NLST` trả text qua TCP.
- **ACTIVE UDP probe (fix LAN):** với Active Mode, client chưa gửi packet UDP nào trước khi server mở START cho RETR (NAT/firewall chưa mở luồng). Sau reply `150` RETR, server gửi một START probe zero-payload dùng đúng endpoint ACTIVE đã negotiation và transfer ID — mở state trên firewall/NAT mà không mang dữ liệu; sau đó luồng Go-Back-N bình thường. Không đổi header, TCP command/reply hay behavior sender.

## 7.4 Test / evidence

- Localhost: `python3 -m pytest tests/test_e2e_transfer.py -q` — **6 passed in 22.63s** (Active, PASV, ba PASV clients song song, ABOR, disconnect).
- Hai máy LAN (09/08/2026): PASV và ACTIVE đều upload+download giữa server `172.18.0.48` và client `172.18.0.49`; SHA-256 source/server/download khớp:
  - `docs/evidence/final-lan-pasv-sha256.txt`
  - `docs/evidence/final-lan-active-sha256.txt`
- Log client/lifecycle: `docs/evidence/final-lan-pasv.log`, `docs/evidence/final-lan-active.log`, `docs/evidence/final-lan-pasv-server.log`.
- ACTIVE download UDP probe: `python3 -m pytest tests/test_e2e_transfer.py::TestEndToEndPasvTransfer::test_active_upload_then_download_preserves_sha256 tests/test_cli_display.py -q` — **8 passed in 5.42s**; full regression **199 passed in 96.72s**.

**DoD:** Bốn hướng transfer (Active/PASV × upload/download) pass với cleanup và không để endpoint stale.
