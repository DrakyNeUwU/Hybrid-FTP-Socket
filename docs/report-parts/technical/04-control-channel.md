# 4. Control Channel — TCP

**Trạng thái:** Complete  
**Mục tiêu:** Trình bày chi tiết kiến trúc TCP control channel, parser, session management, 28-command compliance matrix, MODE negotiation, và FTP reply mapping.  
**Requirement:** RQ-02, RQ-03, RQ-05, RQ-10. **Owner:** Role A. **Reviewer:** Role C.  
**Code:** `server/command_parser.py`, `server/command_handler.py`, `server/session.py`, `server/client_handler.py`, `server/ftp_reply.py`.

---

## 4.1 Architecture & Pipeline Design

Kênh điều khiển (Control Channel) của Hybrid FTP Server hoạt động hoàn toàn trên giao thức TCP dedicated connection cho mỗi client session. Kiến trúc được thiết kế theo nguyên lý Đơn trách nhiệm (Single Responsibility Principle - SRP):

```
Client TCP Socket ──> ClientHandler (Buffer & CRLF Framing)
                            │
                            ▼
                    CommandParser (Parse Command Name & Argument)
                            │
                            ▼
                    CommandHandler (Dispatch & Validate)
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
     Session Object               FilesystemService / TransferManager
(Per-Client Isolated State)          (Path Safety & RDT Data Path)
```

### 1. TCP Framing & Buffering (`ClientHandler`)
- TCP socket nhận các dòng byte thô qua `recv()`. `ClientHandler` duy trì một buffer riêng cho từng client, thực hiện tách lệnh theo ký tự kết thúc `\r\n`.
- Xử lý các ca biên đặc thù của TCP stream:
  - **Fragmented command:** Lệnh bị ngắt giữa chừng qua 2 lần `recv()`.
  - **Coalesced commands:** Nhiều lệnh được gửi gộp trong 1 lần `recv()`.
  - **UnicodeDecodeError:** Bắt ngoại lệ giải mã UTF-8 để không crash client thread khi nhận dữ liệu rác.

### 2. Command Parsing (`CommandParser`)
- `CommandParser` tách chuỗi lệnh thành tên lệnh (`name`) chuyển thành chữ hoa (case-insensitive per RFC 959) và tham số (`argument`).

### 3. Per-Client Session State (`Session`)
- Mỗi kết nối client sở hữu một đối tượng `Session` độc lập, cô lập hoàn toàn trạng thái giữa các client đồng thời:
  - `username`, `is_logged_in`: Trạng thái xác thực.
  - `current_dir`, `ftp_root`: Thư mục làm việc hiện tại và thư mục gốc FTP.
  - `transfer_type` (`I`/`A`), `transfer_mode` (`S`): Kiểu và chế độ truyền dữ liệu.
  - `data_host`, `data_port`, `data_mode` (`ACTIVE`/`PASSIVE`), `data_socket`: Thông tin UDP data channel.
  - `session_id`, `transfer_cancel_event`, `current_transfer`: Định danh session và kiểm soát hủy lệnh ngầm.

---

## 4.2 Authentication & Command Compliance Matrix (28 Lệnh)

Hệ thống hỗ trợ đầy đủ 28 lệnh FTP tiêu chuẩn theo yêu cầu bài tập (§2.2):

| STT | Lệnh | Mô tả | Tham số | Mã Reply Thành công / Lỗi |
|:---:|:---|:---|:---:|:---|
| 1 | `USER` | Tên đăng nhập | Bắt buộc | `331 Password required` / `501` |
| 2 | `PASS` | Mật khẩu đăng nhập | Bắt buộc | `230 Login OK` / `530 Login incorrect`, `503` |
| 3 | `QUIT` | Ngắt kết nối | Không có | `221 Goodbye` / `501` |
| 4 | `NOOP` | Lệnh kiểm tra sống | Không có | `200 NOOP OK` / `501` |
| 5 | `PWD` | Xem thư mục hiện tại | Không có | `257 "/path"` / `530`, `550` |
| 6 | `CWD` | Chuyển thư mục | Bắt buộc | `250 Directory changed` / `501`, `530`, `550` |
| 7 | `CDUP` | Lên thư mục cha | Không có | `200 Directory changed to parent` / `501`, `530`, `550` |
| 8 | `MKD` | Tạo thư mục | Bắt buộc | `257 Directory created` / `501`, `530`, `550` |
| 9 | `RMD` | Xóa thư mục | Bắt buộc | `250 Directory removed` / `501`, `530`, `550` |
| 10 | `DELE` | Xóa file | Bắt buộc | `250 File deleted` / `501`, `530`, `550` |
| 11 | `RNFR` | Chọn file để đổi tên | Bắt buộc | `350 Ready for RNTO` / `501`, `530`, `550` |
| 12 | `RNTO` | Đổi tên file đã chọn | Bắt buộc | `250 Rename successful` / `501`, `503`, `530`, `550` |
| 13 | `LIST` | Xem chi tiết danh sách file (Unix detailed) | Tuỳ chọn | `150 ... 226 Directory send OK` / `530`, `550` |
| 14 | `NLST` | Xem danh sách tên file | Tuỳ chọn | `150 ... 226 Directory send OK` / `530`, `550` |
| 15 | `SIZE` | Kích thước file (bytes) | Bắt buộc | `213 <size>` / `501`, `530`, `550` |
| 16 | `MDTM` | Thời gian sửa đổi file | Bắt buộc | `213 YYYYMMDDhhmmss` / `501`, `530`, `550` |
| 17 | `STAT` | Trạng thái server / file | Tuỳ chọn | `211-FTP Server status` / `530` |
| 18 | `HASH` | Kiểm tra checksum SHA-256 | Bắt buộc | `213 SHA256 <hash>` / `501`, `530`, `550` |
| 19 | `TYPE` | Chọn kiểu truyền (`A`/`I`) | Bắt buộc | `200 Type set` / `501`, `530` |
| 20 | `MODE` | Chế độ truyền (`S`/`B`/`C`) | Bắt buộc | `200 Mode Stream` / `502` (B/C), `501`, `530` |
| 21 | `HELP` | Trợ giúp danh sách lệnh | Tuỳ chọn | `214-Supported commands` / `214` |
| 22 | `PORT` | Cấu hình Active Mode UDP | Bắt buộc | `200 PORT successful` / `501` (syntax/range), `504` (bounce) |
| 23 | `PASV` | Cấu hình Passive Mode UDP | Không có | `227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)` / `425`, `501` |
| 24 | `RETR` | Download file qua UDP/RDT | Bắt buộc | `150 ... 226 Transfer complete` / `425`, `450`, `426`, `550` |
| 25 | `STOR` | Upload file qua UDP/RDT | Bắt buộc | `150 ... 226 Transfer complete` / `425`, `450`, `426`, `550` |
| 26 | `STOU` | Upload file tên duy nhất | Tuỳ chọn | `150 ... 226 Transfer complete` / `425`, `450`, `426`, `550` |
| 27 | `APPE` | Upload nối tiếp vào file | Bắt buộc | `150 ... 226 Transfer complete` / `425`, `450`, `426`, `550` |
| 28 | `ABOR` | Hủy tiến trình truyền dữ liệu | Không có | `226 Abort successful` / `501`, `530` |

---

## 4.3 `MODE` Negotiation Compliance & Limitation (Task A-F01)

- **`MODE S` (Stream Mode):** Được hỗ trợ đầy đủ. Lệnh `MODE S` trả về `200 Mode Stream\r\n` và cập nhật `session.transfer_mode = "S"`.
- **`MODE B` (Block Mode) & `MODE C` (Compressed Mode):** Bài tập không yêu cầu định nghĩa codec nén hoặc framing block ở tầng data. Theo nguyên tắc trung thực technical report, hệ thống **không báo thành công giả (không trả 200)** cho `MODE B/C` mà trả về mã chuẩn:
  ```text
  502 Mode not implemented
  ```
- **Session Isolation:** Cấu hình MODE được lưu trữ độc lập trong từng `Session` đối tượng, việc chuyển MODE ở Client A không làm thay đổi trạng thái của Client B.

---

## 4.4 Flow Control & Transfer Lifecycle (Task A-F02)

1. **Chuỗi phản hồi Transfer (`150 -> 226` / `4xx`):**
   - Khi nhận `RETR`/`STOR`/`STOU`/`APPE`, `CommandHandler` kiểm tra đã có kết nối data connection chưa (`PORT`/`PASV`). Nếu chưa có, trả `425 Use PORT or PASV first\r\n`.
   - Nếu hợp lệ, hệ thống gửi phản hồi `150 Opening data connection\r\n` lập tức trên kênh TCP control, sau đó kích hoạt daemon worker thread thực hiện truyền tải UDP/RDT ngầm.
   - Khi hoàn tất thành công, worker thread gửi `226 Transfer complete\r\n`. Nếu lỗi hoặc bị hủy bởi `ABOR`, gửi `426` hoặc `550`.

2. **Xử lý `ABOR` (Abort Transfer):**
   - `ABOR` có thể gửi bất kỳ lúc nào trên TCP control channel ngay cả khi transfer thread đang chạy.
   - `ABOR` gọi `TransferManager.cancel(session)` để set `session.transfer_cancel_event` và đóng socket data UDP, giải phóng tài nguyên ngầm và join worker thread với timeout hữu hạn.

---

## 4.5 Verification & Unit Testing Evidence

Toàn bộ chức năng của Kênh điều khiển TCP được bảo đảm bằng bộ kiểm thử tự động với 100% pass rate:
- `tests/test_command_parser.py`: Phân tích cú pháp lệnh.
- `tests/test_session.py`: Cô lập dữ liệu giữa các session client.
- `tests/test_commands.py`: Bao phủ toàn bộ 28 lệnh FTP, bao gồm TCP framing, argument validation, auth reset, anti-FTP bounce PORT check, và `TestModeComplianceRoleA` / `TestCommandMatrix28RoleA`.

