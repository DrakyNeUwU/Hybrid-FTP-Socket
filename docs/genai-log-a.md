# GenAI Usage Log — Role A

Format mỗi lần dùng AI:

## [Ngày] - [Tên chức năng]
**Prompt:** ...
**Raw output:** ...
**Refinement:** (mình đã sửa/hiểu gì, lỗi/hạn chế phát hiện được)

# GenAI Usage Log — Role A

## [05/08/2026] - Refactor TCP Command Handler
**Prompt:**
Thiết kế lại phần xử lý lệnh FTP theo hướng tách `ClientHandler`, `CommandHandler`, `CommandParser` và `Session`, đảm bảo mỗi client có session riêng và dễ mở rộng thêm command.

**Raw output:**
AI đề xuất tách mã nguồn thành các module:
- `client_handler.py`
- `command_handler.py`
- `command_parser.py`
- `session.py`

Đồng thời gợi ý chuyển toàn bộ xử lý lệnh từ `threaded_server.py` sang `CommandHandler` để giảm độ phụ thuộc và dễ bảo trì.

**Refinement:**
Đã điều chỉnh lại cấu trúc thư mục cho phù hợp với project, sửa lại constructor của `Session`, bổ sung `FTPReply`, sửa lỗi import và indentation, đồng thời kiểm thử lại bằng Telnet.

---

## [05/08/2026] - Session Management
**Prompt:**
Thiết kế lớp Session để quản lý trạng thái FTP của từng client theo chuẩn FTP.

**Raw output:**
AI đề xuất Session gồm:
- username
- is_logged_in
- current_dir
- ftp_root
- transfer_type
- transfer_mode
- data_host
- data_port
- current_transfer
- transfer_cancelled

**Refinement:**
Bổ sung thêm `rename_from`, `data_socket` và khởi tạo mặc định cho TYPE = I, MODE = S. Kiểm tra hoạt động thông qua các lệnh USER, PASS, TYPE, MODE, CWD và PWD.

---

## [05/08/2026] - FTP Command Implementation
**Prompt:**
Viết skeleton cho các lệnh FTP của Role A gồm PWD, CWD, CDUP, MKD, RMD, LIST, NLST, TYPE, MODE, PORT, PASV, HASH, RNFR, RNTO, RETR, STOR, STOU, APPE và ABOR.

**Raw output:**
AI sinh các hàm xử lý command cùng FTP reply code tương ứng.

**Refinement:**
Đã sửa lại reply code theo yêu cầu đề, kiểm tra điều kiện đăng nhập trước khi thực thi lệnh, xử lý các trường hợp thiếu tham số, đường dẫn không tồn tại và chuẩn hóa response theo FTP.

---

## [05/08/2026] - Multi-threaded Server
**Prompt:**
Cải tiến threaded_server.py để hỗ trợ nhiều client đồng thời, quản lý session và cleanup tài nguyên khi client ngắt kết nối.

**Raw output:**
AI đề xuất:
- danh sách active clients
- session id
- cleanup()
- register/unregister client
- thread-safe logging

**Refinement:**
Đã tích hợp vào `threaded_server.py`, bổ sung `SO_REUSEADDR`, timeout cho `accept()`, quản lý session theo từng client và kiểm thử bằng nhiều kết nối Telnet đồng thời.

---

## [05/08/2026] - Functional Testing
**Prompt:**
Hướng dẫn kiểm thử toàn bộ command của FTP server bằng Telnet.

**Raw output:**
AI đưa ra các kịch bản kiểm thử cho:
- Authentication
- Directory commands
- TYPE/MODE
- LIST/NLST
- HASH
- Rename
- PASV/PORT
- QUIT

**Refinement:**
Đã thực hiện kiểm thử thực tế trên Linux bằng Telnet, sửa các lỗi phát sinh (IndentationError, Session constructor, import, reply code, path handling) cho đến khi các command hoạt động đúng.

---

## [07/08/2026] - TCP Framing Buffer (tuần 2.5)
**Prompt:**
Sửa `ClientHandler` để buffer đầu vào TCP đúng chuẩn: mỗi lần `recv()` có thể nhận nửa command hoặc nhiều command cùng lúc, cần tách bằng `\r\n`.

**Raw output:**
AI đề xuất thêm `self.buffer = b""` vào `__init__`, trong vòng lặp `run()` cộng dồn dữ liệu vào buffer rồi dùng `split(b"\r\n", 1)` để tách từng command hoàn chỉnh.

**Refinement:**
Đã tích hợp vào `client_handler.py`. Bổ sung bắt `UnicodeDecodeError` cho từng command để không crash thread khi client gửi byte không hợp lệ. Kiểm thử bằng unit test mô phỏng hai command trong một `recv()` và command bị split giữa hai `recv()`.

---

## [07/08/2026] - Filesystem Service Integration (tuần 2.5)
**Prompt:**
Thay toàn bộ `os.path.join`, `os.listdir`, `os.mkdir`, `os.rmdir`, `os.remove`, `os.rename` trong `command_handler.py` bằng `FilesystemService` của Role C để đảm bảo chặn path traversal, symlink escape và prefix collision.

**Raw output:**
AI đề xuất thêm helper `_fs(session)` trong `CommandHandler` trả về `transfer_manager.filesystem` khi có `TransferManager`, hoặc tạo `_FallbackFilesystem` theo `session.ftp_root` khi chạy unit test không có `TransferManager`.

**Refinement:**
Đã thêm `_FallbackFilesystem` và `_FallbackTransferManager` làm shim test-only. Tất cả lệnh `CWD`, `MKD`, `RMD`, `DELE`, `RNFR/RNTO`, `LIST`, `NLST`, `SIZE`, `MDTM`, `HASH`, `RETR`, `STOR`, `STOU`, `APPE` đều đi qua `_fs(session)`. Chạy 110 test pass xác nhận không regression.

---

## [07/08/2026] - LIST Detailed Format (tuần 2.5)
**Prompt:**
Sửa lệnh `LIST` để trả Unix-style detailed listing có name, size, type (`d`/`-`), permissions và modified time; phân biệt rõ với `NLST` chỉ trả tên.

**Raw output:**
AI đề xuất dùng kết quả từ `filesystem_service.list_directory()` (trả dict có `name`, `size`, `type`, `permissions`, `modified`) và format theo chuẩn `drwxr-xr-x  1 ftp ftp       SIZE  Mon DD HH:MM NAME`.

**Refinement:**
Đã sửa `list_dir()` để parse dict từ `FilesystemService` và định dạng đúng. Bổ sung fallback cho `SimpleNamespace` trong trường hợp test dùng shim. Thêm 5 unit test kiểm tra prefix `d`/`-`, size và format `150/226`.

---

## [07/08/2026] - PASV/PORT/ABOR/Cleanup (tuần 2.5)
**Prompt:**
Sửa `PASV` đóng socket cũ trước khi tạo mới, `PORT` validate đủ 6 số 0–255 và port > 0, `ABOR` gọi `TransferManager.cancel()`, `cleanup()` dọn data socket và reset toàn bộ state.

**Raw output:**
AI đề xuất code cụ thể cho từng hàm với try/except rõ ràng và cleanup trong `finally`.

**Refinement:**
Đã tích hợp vào `client_handler.py` và `command_handler.py`. `rename_from` được reset khi bất kỳ command nào khác `RNTO` được gọi sau `RNFR`, kể cả `QUIT` và `disconnect`. Kiểm thử bằng unit test `TestRenameFromReset`.

---

## [07/08/2026] - Transfer Threading (tuần 2.5)
**Prompt:**
Sửa `STOR`, `RETR`, `STOU`, `APPE` để trả `150` ngay lập tức rồi chạy RDT trong thread riêng, gửi `226`/`426` sau khi xong.

**Raw output:**
AI đề xuất helper `_start_transfer_thread()` tạo `threading.Thread(daemon=True)`, gọi `session.send_reply()` từ trong thread sau khi transfer xong.

**Refinement:**
Đã implement và tích hợp. `session.send_reply` được inject từ `ClientHandler.send` khi khởi tạo. TCP command thread tiếp tục nhận lệnh (kể cả `ABOR`) trong khi transfer thread chạy ngầm. Xác nhận bằng test `test_transfer_manager.py` pass.

---

## [07/08/2026] - Auth Reset, PORT/PASV Fix, RNTO Reset (tuần 2.5 — audit)
**Prompt:**
Sau audit, tìm thấy các lỗi còn thiếu trong checklist 11.1: (1) `USER` mới không reset login state; (2) password sai không clear username; (3) PORT dùng `except:` trống; (4) PASV luôn quảng bá `127.0.0.1` thay vì IP server thật; (5) RNTO thiếu arg không reset `rename_from`; (6) `_start_transfer_thread` dùng `result.reply_code` khi result là falsy nhưng `None`; (7) `abor` crash khi `transfer_manager` là None. Sửa tất cả và thêm test đầy đủ.

**Raw output:**
AI đề xuất:
- `user()`: thêm `session.is_logged_in = False; session.rename_from = None` trước khi set username mới.
- `password()`: thêm check `if session.is_logged_in: return "230 Already logged in"`; khi sai pass thêm `session.username = None`.
- `port_cmd()`: build danh sách `nums[]` với `int()`, validate từng số, thêm kiểm tra `port <= 0 or port > 65535`, catch `(ValueError, IndexError)` thay vì `except:`.
- `pasv()`: thêm `session.data_socket = None` sau khi close, dùng `socket.gethostbyname(socket.gethostname())` để lấy IP thật, format 227 với IP thật.
- `rnto()`: khi `not arg`, set `session.rename_from = None` trước khi return 501.
- `_start_transfer_thread`: phân biệt ba trường hợp `result` truthy, falsy-non-None, và `None`.
- `abor()`: dùng `tm = self.transfer_manager or getattr(self, '_tm', None)` để tránh crash khi None.

**Refinement:**
Tất cả sửa đổi được tích hợp. Bổ sung 20 unit test mới trong `tests/test_commands.py` cho: PORT validation (valid, too few, out of range, negative, port zero, non-numeric, no arg), auth reset (new USER clears login, wrong password clears username, PASS before USER returns 503), RNTO empty arg resets state, PASV socket replacement (creates socket, replaces old one), TYPE/MODE validation (valid A/I, invalid Z, mode B/C returns 502, invalid X). Tổng: **48 tests pass**.

---

## [07/08/2026] - RDT Adapters, Complete Filesystem Integration & ABOR Cleanup (tuần 2.5 — Hoàn tất Role A)
**Prompt:**
Hoàn thiện toàn bộ các task Role A trong `tuan-2.5-fix.md`: (1) Viết `RDTSenderAdapter` và `RDTReceiverAdapter` nối RDT UDP sockets với `TransferManager`; (2) Inject adapters vào `TransferManager` trong `ClientHandler`; (3) Chuyển toàn bộ các lệnh `SIZE`, `MDTM`, `HASH`, `CWD`, `CDUP`, `MKD`, `RMD`, `DELE`, `RNFR/RNTO`, `LIST`, `NLST` sang `FilesystemService`; (4) Validate số lượng tham số đồng nhất cho mọi command (từ chối tham số thừa cho PWD/NOOP/QUIT/PASV/CDUP/ABOR, trả 501 cho lệnh thiếu tham số); (5) Áp dụng Anti-FTP bounce IP policy cho `PORT`; (6) Kiểm tra data connection trước khi trả 150 cho các lệnh transfer (`RETR`, `STOR`, `STOU`, `APPE`); (7) Hủy transfer và join worker thread hữu hạn khi `ABOR` hoặc `cleanup()`.

**Raw output:**
AI đề xuất:
- Tạo module `server/rdt_adapter.py` cung cấp `RDTSenderAdapter` và `RDTReceiverAdapter` sử dụng `RDTHeader`.
- Inject hai adapter này vào `TransferManager` trong `ClientHandler.__init__`.
- Cập nhật `CommandHandler` sử dụng `FilesystemService` độc quyền và bắt `FilesystemOperationError` để map reply code chuẩn.
- Kiểm tra `session.data_socket` và `session.data_host` trước khi khởi chạy thread transfer, trả `425` nếu chưa có data connection.
- Thêm `TestRoleAValidationAndRDTAdapter` kiểm thử toàn bộ các nhánh validation và adapter.

**Refinement:**
Đã tạo `server/rdt_adapter.py`, cập nhật `server/transfer_manager.py`, `server/client_handler.py`, `server/command_handler.py`, và bổ sung các unit test mới trong `tests/test_commands.py`. Toàn bộ test suite pass 100%.