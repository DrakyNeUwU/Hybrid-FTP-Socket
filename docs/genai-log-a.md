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