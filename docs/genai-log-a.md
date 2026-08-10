# GenAI Usage Log — Role A

> **Format (strict requirement):** mỗi mục ghi **Exact prompt** (prompt gốc,
> nguyên văn, chưa chỉnh sửa), **Raw GenAI output** (đầu ra AI gốc, unedited —
> code blocks giữ nguyên verbatim), **Review and refinement** (tinh chỉnh thủ
> công của Role A sau khi kiểm thử) và **Verification** (bằng chứng test thực).

## [05/08/2026] - Refactor TCP Command Handler
**Exact prompt:**
> "Thiết kế lại phần xử lý lệnh FTP theo hướng tách `ClientHandler`, `CommandHandler`, `CommandParser` và `Session`, đảm bảo mỗi client có session riêng và dễ mở rộng thêm command."

**Raw GenAI output:**
AI đề xuất tách mã nguồn thành các module:
- `client_handler.py`
- `command_handler.py`
- `command_parser.py`
- `session.py`

Đồng thời gợi ý chuyển toàn bộ xử lý lệnh từ `threaded_server.py` sang `CommandHandler` để giảm độ phụ thuộc và dễ bảo trì.

**Review and refinement:**
Đã điều chỉnh lại cấu trúc thư mục cho phù hợp với project, sửa lại constructor của `Session`, bổ sung `FTPReply`, sửa lỗi import và indentation, đồng thời kiểm thử lại bằng Telnet.

---
## [05/08/2026] - Session Management
**Exact prompt:**
> "Thiết kế lớp Session để quản lý trạng thái FTP của từng client theo chuẩn FTP."

**Raw GenAI output:**
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

**Review and refinement:**
Bổ sung thêm `rename_from`, `data_socket` và khởi tạo mặc định cho TYPE = I, MODE = S. Kiểm tra hoạt động thông qua các lệnh USER, PASS, TYPE, MODE, CWD và PWD.

---

## [05/08/2026] - FTP Command Implementation
**Exact prompt:**
> "Viết skeleton cho các lệnh FTP của Role A gồm PWD, CWD, CDUP, MKD, RMD, LIST, NLST, TYPE, MODE, PORT, PASV, HASH, RNFR, RNTO, RETR, STOR, STOU, APPE và ABOR."

**Raw GenAI output:**
AI sinh các hàm xử lý command cùng FTP reply code tương ứng.

**Review and refinement:**
Đã sửa lại reply code theo yêu cầu đề, kiểm tra điều kiện đăng nhập trước khi thực thi lệnh, xử lý các trường hợp thiếu tham số, đường dẫn không tồn tại và chuẩn hóa response theo FTP.

---

## [05/08/2026] - Multi-threaded Server
**Exact prompt:**
> "Cải tiến threaded_server.py để hỗ trợ nhiều client đồng thời, quản lý session và cleanup tài nguyên khi client ngắt kết nối."

**Raw GenAI output:**
AI đề xuất:
- danh sách active clients
- session id
- cleanup()
- register/unregister client
- thread-safe logging

**Review and refinement:**
Đã tích hợp vào `threaded_server.py`, bổ sung `SO_REUSEADDR`, timeout cho `accept()`, quản lý session theo từng client và kiểm thử bằng nhiều kết nối Telnet đồng thời.

---

## [05/08/2026] - Functional Testing
**Exact prompt:**
> "Hướng dẫn kiểm thử toàn bộ command của FTP server bằng Telnet."

**Raw GenAI output:**
AI đưa ra các kịch bản kiểm thử cho:
- Authentication
- Directory commands
- TYPE/MODE
- LIST/NLST
- HASH
- Rename
- PASV/PORT
- QUIT

**Review and refinement:**
Đã thực hiện kiểm thử thực tế trên Linux bằng Telnet, sửa các lỗi phát sinh (IndentationError, Session constructor, import, reply code, path handling) cho đến khi các command hoạt động đúng.

---

## [07/08/2026] - TCP Framing Buffer (tuần 2.5)
**Exact prompt:**
> "Sửa `ClientHandler` để buffer đầu vào TCP đúng chuẩn: mỗi lần `recv()` có thể nhận nửa command hoặc nhiều command cùng lúc, cần tách bằng `\r\n`."

**Raw GenAI output:**
AI đề xuất thêm `self.buffer = b""` vào `__init__`, trong vòng lặp `run()` cộng dồn dữ liệu vào buffer rồi dùng `split(b"\r\n", 1)` để tách từng command hoàn chỉnh.

**Review and refinement:**
Đã tích hợp vào `client_handler.py`. Bổ sung bắt `UnicodeDecodeError` cho từng command để không crash thread khi client gửi byte không hợp lệ. Kiểm thử bằng unit test mô phỏng hai command trong một `recv()` và command bị split giữa hai `recv()`.

---

## [07/08/2026] - Filesystem Service Integration (tuần 2.5)
**Exact prompt:**
> "Thay toàn bộ `os.path.join`, `os.listdir`, `os.mkdir`, `os.rmdir`, `os.remove`, `os.rename` trong `command_handler.py` bằng `FilesystemService` của Role C để đảm bảo chặn path traversal, symlink escape và prefix collision."

**Raw GenAI output:**
AI đề xuất thêm helper `_fs(session)` trong `CommandHandler` trả về `transfer_manager.filesystem` khi có `TransferManager`, hoặc tạo `_FallbackFilesystem` theo `session.ftp_root` khi chạy unit test không có `TransferManager`.

**Review and refinement:**
Đã thêm `_FallbackFilesystem` và `_FallbackTransferManager` làm shim test-only. Tất cả lệnh `CWD`, `MKD`, `RMD`, `DELE`, `RNFR/RNTO`, `LIST`, `NLST`, `SIZE`, `MDTM`, `HASH`, `RETR`, `STOR`, `STOU`, `APPE` đều đi qua `_fs(session)`. Chạy 110 test pass xác nhận không regression.

---

## [07/08/2026] - LIST Detailed Format (tuần 2.5)
**Exact prompt:**
> "Sửa lệnh `LIST` để trả Unix-style detailed listing có name, size, type (`d`/`-`), permissions và modified time; phân biệt rõ với `NLST` chỉ trả tên."

**Raw GenAI output:**
AI đề xuất dùng kết quả từ `filesystem_service.list_directory()` (trả dict có `name`, `size`, `type`, `permissions`, `modified`) và format theo chuẩn `drwxr-xr-x  1 ftp ftp       SIZE  Mon DD HH:MM NAME`.

**Review and refinement:**
Đã sửa `list_dir()` để parse dict từ `FilesystemService` và định dạng đúng. Bổ sung fallback cho `SimpleNamespace` trong trường hợp test dùng shim. Thêm 5 unit test kiểm tra prefix `d`/`-`, size và format `150/226`.

---

## [07/08/2026] - PASV/PORT/ABOR/Cleanup (tuần 2.5)
**Exact prompt:**
> "Sửa `PASV` đóng socket cũ trước khi tạo mới, `PORT` validate đủ 6 số 0–255 và port > 0, `ABOR` gọi `TransferManager.cancel()`, `cleanup()` dọn data socket và reset toàn bộ state."

**Raw GenAI output:**
AI đề xuất code cụ thể cho từng hàm với try/except rõ ràng và cleanup trong `finally`.

**Review and refinement:**
Đã tích hợp vào `client_handler.py` và `command_handler.py`. `rename_from` được reset khi bất kỳ command nào khác `RNTO` được gọi sau `RNFR`, kể cả `QUIT` và `disconnect`. Kiểm thử bằng unit test `TestRenameFromReset`.

---

## [07/08/2026] - Transfer Threading (tuần 2.5)
**Exact prompt:**
> "Sửa `STOR`, `RETR`, `STOU`, `APPE` để trả `150` ngay lập tức rồi chạy RDT trong thread riêng, gửi `226`/`426` sau khi xong."

**Raw GenAI output:**
AI đề xuất helper `_start_transfer_thread()` tạo `threading.Thread(daemon=True)`, gọi `session.send_reply()` từ trong thread sau khi transfer xong.

**Review and refinement:**
Đã implement và tích hợp. `session.send_reply` được inject từ `ClientHandler.send` khi khởi tạo. TCP command thread tiếp tục nhận lệnh (kể cả `ABOR`) trong khi transfer thread chạy ngầm. Xác nhận bằng test `test_transfer_manager.py` pass.

---

## [07/08/2026] - Auth Reset, PORT/PASV Fix, RNTO Reset (tuần 2.5 — audit)
**Exact prompt:**
> "Sau audit, tìm thấy các lỗi còn thiếu trong checklist 11.1: (1) `USER` mới không reset login state; (2) password sai không clear username; (3) PORT dùng `except:` trống; (4) PASV luôn quảng bá `127.0.0.1` thay vì IP server thật; (5) RNTO thiếu arg không reset `rename_from`; (6) `_start_transfer_thread` dùng `result.reply_code` khi result là falsy nhưng `None`; (7) `abor` crash khi `transfer_manager` là None. Sửa tất cả và thêm test đầy đủ."

**Raw GenAI output:**
AI đề xuất:
- `user()`: thêm `session.is_logged_in = False; session.rename_from = None` trước khi set username mới.
- `password()`: thêm check `if session.is_logged_in: return "230 Already logged in"`; khi sai pass thêm `session.username = None`.
- `port_cmd()`: build danh sách `nums[]` với `int()`, validate từng số, thêm kiểm tra `port <= 0 or port > 65535`, catch `(ValueError, IndexError)` thay vì `except:`.
- `pasv()`: thêm `session.data_socket = None` sau khi close, dùng `socket.gethostbyname(socket.gethostname())` để lấy IP thật, format 227 với IP thật.
- `rnto()`: khi `not arg`, set `session.rename_from = None` trước khi return 501.
- `_start_transfer_thread`: phân biệt ba trường hợp `result` truthy, falsy-non-None, và `None`.
- `abor()`: dùng `tm = self.transfer_manager or getattr(self, '_tm', None)` để tránh crash khi None.

**Review and refinement:**
Tất cả sửa đổi được tích hợp. Bổ sung 20 unit test mới trong `tests/test_commands.py` cho: PORT validation (valid, too few, out of range, negative, port zero, non-numeric, no arg), auth reset (new USER clears login, wrong password clears username, PASS before USER returns 503), RNTO empty arg resets state, PASV socket replacement (creates socket, replaces old one), TYPE/MODE validation (valid A/I, invalid Z, mode B/C returns 502, invalid X). Tổng: **48 tests pass**.

---

## [07/08/2026] - RDT Adapters, Complete Filesystem Integration & ABOR Cleanup (tuần 2.5 — Hoàn tất Role A)
**Exact prompt:**
> "Hoàn thiện toàn bộ các task Role A trong `tuan-2.5-fix.md`: (1) Viết `RDTSenderAdapter` và `RDTReceiverAdapter` nối RDT UDP sockets với `TransferManager`; (2) Inject adapters vào `TransferManager` trong `ClientHandler`; (3) Chuyển toàn bộ các lệnh `SIZE`, `MDTM`, `HASH`, `CWD`, `CDUP`, `MKD`, `RMD`, `DELE`, `RNFR/RNTO`, `LIST`, `NLST` sang `FilesystemService`; (4) Validate số lượng tham số đồng nhất cho mọi command (từ chối tham số thừa cho PWD/NOOP/QUIT/PASV/CDUP/ABOR, trả 501 cho lệnh thiếu tham số); (5) Áp dụng Anti-FTP bounce IP policy cho `PORT`; (6) Kiểm tra data connection trước khi trả 150 cho các lệnh transfer (`RETR`, `STOR`, `STOU`, `APPE`); (7) Hủy transfer và join worker thread hữu hạn khi `ABOR` hoặc `cleanup()`."

**Raw GenAI output:**
AI đề xuất:
- Tạo module `server/rdt_adapter.py` cung cấp `RDTSenderAdapter` và `RDTReceiverAdapter` sử dụng `RDTHeader`.
- Inject hai adapter này vào `TransferManager` trong `ClientHandler.__init__`.
- Cập nhật `CommandHandler` sử dụng `FilesystemService` độc quyền và bắt `FilesystemOperationError` để map reply code chuẩn.
- Kiểm tra `session.data_socket` và `session.data_host` trước khi khởi chạy thread transfer, trả `425` nếu chưa có data connection.
- Thêm `TestRoleAValidationAndRDTAdapter` kiểm thử toàn bộ các nhánh validation và adapter.

**Review and refinement:**
Đã tạo `server/rdt_adapter.py`, cập nhật `server/transfer_manager.py`, `server/client_handler.py`, `server/command_handler.py`, và bổ sung các unit test mới trong `tests/test_commands.py`. Toàn bộ test suite pass 100%.

---

## [07/08/2026] - Sửa Import Package (tuần 2.5 — Phase 0)

**Exact prompt:**
> "Các module trong `server/` bị lỗi import khi chạy từ repository root. Nguyên nhân là các file dùng `sys.path.insert` và relative import sai. Hãy sửa toàn bộ import trong `server/threaded_server.py`, `server/client_handler.py`, `server/command_handler.py` về chuẩn package Python để lệnh `python -c "import server.threaded_server"` chạy thành công từ thư mục gốc mà không cần `sys.path` hack."

**Raw GenAI output:**
AI chỉ ra rằng cần:
- Thay `from client_handler import ClientHandler` thành `from server.client_handler import ClientHandler`.
- Thay `from command_handler import CommandHandler` thành `from server.command_handler import CommandHandler`.
- Tất cả import nội bộ trong `server/` phải dùng `from server.<module> import ...`.
- Đảm bảo `server/__init__.py` tồn tại (có thể rỗng).
- Xóa mọi `sys.path.insert(0, ...)` trong các module production.

**Review and refinement:**
Đã sửa lần lượt từng file. Riêng `server/command_handler.py` cần import `from common.filesystem_service import FilesystemService` thay vì path tương đối. Sau khi sửa, lệnh `python -c "import server.threaded_server"` pass từ repo root. Ghi chú: startup thực tế trên Linux/WSL2 chưa được xác nhận do máy thật chưa cài đủ dependencies — sẽ tick khi có bằng chứng.

---

## [07/08/2026] - Hoàn thiện TransferManager.upload() và download() (tuần 2.5)

**Exact prompt:**
> "`TransferManager.upload()` và `download()` hiện chỉ là `pass`. Hãy implement đầy đủ hai phương thức này:
> - `upload()` nhận dữ liệu từ client qua `receiver.receive(data_socket, endpoint, cancel_event)` (trả về `Iterable[bytes]`), sau đó giao cho `FilesystemService` ghi file.
> - `download()` đọc dữ liệu từ `FilesystemService.read_chunks(path)`, rồi gọi `sender.send(chunks, data_socket, endpoint, cancel_event)` để gửi qua UDP/RDT.
> - `upload_unique()` dùng `FilesystemService.upload_unique()` để tạo tên không trùng.
> - `append()` dùng `FilesystemService.append()` với per-path lock.
> - `cancel(session)` set `session.transfer_cancel_event`, đóng `session.data_socket` và để filesystem dọn `.part`.
> - Bỏ fallback `try/except TypeError` trong `_invoke()`; validate sender/receiver ngay khi inject.
> - `TransferResult` phải có: `success`, `reply_code`, `bytes_transferred`, `path`, `error`."

**Raw GenAI output:**
AI sinh code đầy đủ cho `TransferManager` với:

```python
class TransferManager:
    def __init__(self, filesystem, sender, receiver):
        self.filesystem = filesystem
        self.sender = sender
        self.receiver = receiver

    def upload(self, session, path, data_socket, endpoint):
        cancel_event = session.transfer_cancel_event
        try:
            chunks = self.receiver.receive(data_socket, endpoint, cancel_event)
            bytes_written = self.filesystem.write(path, chunks)
            return TransferResult(success=True, reply_code=226,
                                  bytes_transferred=bytes_written, path=path)
        except FilesystemOperationError as e:
            return TransferResult(success=False, reply_code=550, error=str(e), path=path)
        except Exception as e:
            return TransferResult(success=False, reply_code=426, error=str(e), path=path)

    def download(self, session, path, data_socket, endpoint):
        cancel_event = session.transfer_cancel_event
        try:
            chunks = self.filesystem.read_chunks(path)
            bytes_sent = self.sender.send(chunks, data_socket, endpoint, cancel_event)
            return TransferResult(success=True, reply_code=226,
                                  bytes_transferred=bytes_sent, path=path)
        except FilesystemOperationError as e:
            return TransferResult(success=False, reply_code=550, error=str(e), path=path)
        except Exception as e:
            return TransferResult(success=False, reply_code=426, error=str(e), path=path)

    def cancel(self, session):
        if session.transfer_cancel_event:
            session.transfer_cancel_event.set()
        if session.data_socket:
            try:
                session.data_socket.close()
            except Exception:
                pass
            session.data_socket = None
```

**Review and refinement:**
Đã tích hợp vào `server/transfer_manager.py`. Bổ sung phân biệt `FilesystemOperationError` (→ `550`) với các lỗi RDT/network (→ `426`). Xóa fallback `try/except TypeError` trong `_invoke()`. Kiểm tra inject đúng sender/receiver bằng `assert callable(getattr(sender, 'send', None))` khi khởi tạo. Confirm bằng `test_transfer_manager.py` pass.

---

## [07/08/2026] - Luồng 150→226 cho RETR/STOR/STOU/APPE (tuần 2.5)

**Exact prompt:**
> "Hiện tại `STOR`/`RETR` trả reply cuối ngay trong TCP thread, không đúng chuẩn FTP. Hãy sửa để:
> 1. Kiểm tra data connection (PORT hoặc PASV đã được thiết lập); nếu không có thì trả `425 Use PORT or PASV first` và dừng.
> 2. Gửi `150 Opening data connection` ngay trên TCP control thread.
> 3. Spawn daemon worker thread để thực hiện RDT transfer + filesystem commit.
> 4. Worker thread gửi `226 Transfer complete` khi thành công hoặc `426 Transfer aborted`/`550 <reason>` khi thất bại.
> 5. TCP control thread tiếp tục nhận lệnh (kể cả `ABOR`) trong khi worker chạy.
> Áp dụng cho cả `RETR`, `STOR`, `STOU`, `APPE`."

**Raw GenAI output:**
AI đề xuất helper:

```python
def _start_transfer_thread(self, session, target_fn, *args):
    """target_fn phải gọi session.send_reply() trước khi return."""
    if not session.data_host and not session.data_socket:
        return "425 Use PORT or PASV first.\r\n"
    session.send_reply("150 Opening data connection.\r\n")
    t = threading.Thread(
        target=self._transfer_worker,
        args=(session, target_fn, args),
        daemon=True,
    )
    session.current_transfer = t
    t.start()
    return None  # reply đã được gửi trong worker

def _transfer_worker(self, session, target_fn, args):
    result = target_fn(session, *args)
    if result and result.success:
        session.send_reply(f"226 Transfer complete. {result.bytes_transferred} bytes.\r\n")
    elif result:
        code = result.reply_code or 426
        session.send_reply(f"{code} {result.error or 'Transfer failed'}.\r\n")
    else:
        session.send_reply("426 Transfer aborted.\r\n")
    session.current_transfer = None
```

**Review and refinement:**
Đã tích hợp vào `server/command_handler.py`. Phân biệt ba nhánh kết quả: `result` truthy (thành công), `result` falsy nhưng không `None` (thất bại có `reply_code`), và `result is None` (hủy/abort). `session.send_reply` được inject từ `ClientHandler.send()` khi khởi tạo handler. Xác nhận bằng test `TestTransferLifecycle` với mock sender/receiver: `150` phải xuất hiện trước `226`/`426` và trong đúng thread.

---

## [07/08/2026] - Bổ sung NOOP, STAT, SIZE, MDTM, HELP (tuần 2.5)

**Exact prompt:**
> "Thêm các lệnh FTP còn thiếu vào `CommandHandler`: `NOOP`, `STAT`, `SIZE`, `MDTM`, `HELP`. Yêu cầu:
> - `NOOP`: trả `200 OK`, không tham số (từ chối thừa với `501`).
> - `STAT` không arg: trả `211` với thông tin server (phiên bản, trạng thái kết nối, TYPE, MODE).
> - `STAT` có path arg: gọi `FilesystemService.stat(path)`, trả listing trong `213`.
> - `SIZE`: gọi `FilesystemService.size(path)`, trả `213 <bytes>`. Lỗi → `550`.
> - `MDTM`: gọi `FilesystemService.mdtm(path)`, trả `213 YYYYMMDDhhmmss`. Lỗi → `550`.
> - `HELP`: trả `214` với danh sách lệnh hỗ trợ.
> Tất cả đều kiểm tra đăng nhập trước; nếu chưa login → `530`."

**Raw GenAI output:**
AI sinh đầy đủ 5 handler function với reply code và format chuẩn FTP. `STAT` với path được xử lý bằng `try/except FilesystemOperationError` và trả `550` nếu lỗi.

**Review and refinement:**
Đã tích hợp. Sửa `STAT` không arg để không yêu cầu login (vẫn trả `211` dù chưa đăng nhập nhưng thông tin bị giới hạn). `MDTM` format thời gian bằng `datetime.strftime('%Y%m%d%H%M%S')`. Thêm 5 unit test cho các lệnh mới. Đăng ký vào dispatcher dict của `CommandHandler`.

---

## [07/08/2026] - Ánh xạ FilesystemOperationError → Reply Code (tuần 2.5)

**Exact prompt:**
> "Hiện tại `command_handler.py` dùng `except Exception: return "550 ..."` bắt tất cả lỗi thành một reply code. Hãy sửa để bắt `FilesystemOperationError` riêng và ánh xạ đúng:
> - `ErrorType.NOT_FOUND` → `550 File not found`
> - `ErrorType.PERMISSION` → `550 Permission denied`
> - `ErrorType.PATH_TRAVERSAL` → `550 Path traversal not allowed`
> - `ErrorType.IO_ERROR` → `451 Local error in processing`
> - `ErrorType.ALREADY_EXISTS` → `553 File name not allowed`"

**Raw GenAI output:**
```python
def _fs_error_reply(e):
    mapping = {
        ErrorType.NOT_FOUND:      "550 File not found.",
        ErrorType.PERMISSION:     "550 Permission denied.",
        ErrorType.PATH_TRAVERSAL: "550 Path traversal not allowed.",
        ErrorType.IO_ERROR:        "451 Local error in processing.",
        ErrorType.ALREADY_EXISTS:  "553 File name not allowed.",
    }
    return mapping.get(e.error_type, "550 Requested action not taken.") + "\r\n"
```

**Review and refinement:**
Đã implement `_fs_error_reply()` và áp dụng cho tất cả handler dùng `FilesystemService`. Loại bỏ toàn bộ `except:` trống; thay bằng `except FilesystemOperationError as e: return self._fs_error_reply(e)` và `except Exception as e: return f"451 {e}\r\n"`. Thêm test kiểm tra từng nhánh reply code cho `CWD`, `DELE`, `RETR`.

---

## [07/08/2026] - Anti-FTP Bounce cho PORT (tuần 2.5)

**Exact prompt:**
> "Lệnh `PORT` hiện chỉ kiểm tra định dạng 6 số nhưng chấp nhận IP tùy ý. Hãy thêm:
> 1. Kiểm tra mỗi số trong `0..255`; port phải `> 0` và `≤ 65535`.
> 2. Từ chối non-numeric với `501 Syntax error in parameters`.
> 3. Anti-FTP bounce: so sánh IP trong lệnh `PORT` với IP TCP peer của client. Nếu khác nhau và IP không nằm trong allowlist (loopback `127.x.x.x` hoặc cùng subnet), trả `504 Command not implemented for that parameter`."

**Raw GenAI output:**
AI đề xuất:

```python
def port_cmd(self, session, arg, peer_ip=None):
    try:
        nums = [int(x) for x in arg.split(',')]
    except (ValueError, AttributeError):
        return "501 Syntax error in parameters.\r\n"
    if len(nums) != 6 or not all(0 <= n <= 255 for n in nums):
        return "501 Syntax error in parameters.\r\n"
    port = nums[4] * 256 + nums[5]
    if port <= 0 or port > 65535:
        return "501 Syntax error in parameters.\r\n"
    ip = '.'.join(str(n) for n in nums[:4])
    if peer_ip and ip != peer_ip and not ip.startswith('127.'):
        return "504 Command not implemented for that parameter.\r\n"
    session.data_host = ip
    session.data_port = port
    session.data_mode = "ACTIVE"
    return "200 PORT command successful.\r\n"
```

**Review and refinement:**
Đã tích hợp. `peer_ip` được truyền từ `ClientHandler` (lấy từ `socket.getpeername()[0]`). Thêm 8 unit test: PORT hợp lệ, thiếu arg, sai format, số âm, số > 255, port = 0, port > 65535, IP khác peer → `504`. Tất cả pass.

---

## [07/08/2026] - PASV Đóng Socket Cũ + Resolve IP Thật (tuần 2.5)

**Exact prompt:**
> "Lệnh `PASV` hiện tạo UDP socket mới mà không đóng socket cũ (rò rỉ file descriptor) và luôn trả `127.0.0.1` thay vì IP server thật. Hãy sửa:
> 1. Đóng `session.data_socket` cũ trước khi tạo socket mới.
> 2. Set `session.data_socket = None` ngay sau khi close.
> 3. Resolve IP server thật bằng `socket.gethostbyname(socket.gethostname())`; fallback `127.0.0.1` nếu lỗi.
> 4. Cleanup toàn bộ endpoint (socket, host, port, mode) khi `QUIT`, disconnect hoặc PORT/PASV lần mới."

**Raw GenAI output:**
AI đề xuất:

```python
def pasv(self, session):
    # Đóng socket cũ
    if session.data_socket:
        try:
            session.data_socket.close()
        except Exception:
            pass
        session.data_socket = None
    # Tạo socket UDP mới
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    _, port = sock.getsockname()
    # Resolve IP thật
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        ip = '127.0.0.1'
    session.data_socket = sock
    session.data_host = ip
    session.data_port = port
    session.data_mode = "PASSIVE"
    p1, p2 = port >> 8, port & 0xFF
    ip_str = ip.replace('.', ',')
    return f"227 Entering Passive Mode ({ip_str},{p1},{p2}).\r\n"
```

**Review and refinement:**
Đã tích hợp. Thêm unit test `TestPasvSocketReplacement`: gọi PASV lần 1 → lần 2, xác nhận socket cũ được đóng (mock `close()` và kiểm tra số lần gọi). Thêm test resolve IP thật (mock `gethostbyname` trả IP khác `127.0.0.1`).

---

## [07/08/2026] - RNFR/RNTO State Reset Toàn Diện (tuần 2.5)

**Exact prompt:**
> "`rename_from` hiện chỉ bị clear khi `RNTO` thành công. Hãy đảm bảo `rename_from = None` trong mọi trường hợp:
> 1. `RNTO` thất bại (path lỗi, filesystem error).
> 2. `RNTO` thiếu tham số → `501` + reset.
> 3. Bất kỳ command nào khác `RNTO` được gọi ngay sau `RNFR` → reset `rename_from` trước khi xử lý command mới.
> 4. `QUIT` → reset.
> 5. Disconnect/cleanup → reset.
> Validate cả source (`RNFR`) và destination (`RNTO`) qua `FilesystemService` để chặn path traversal."

**Raw GenAI output:**
AI đề xuất thêm guard đầu dispatcher:

```python
def dispatch(self, session, command, arg):
    # Reset rename state nếu command không phải RNTO
    if command != 'RNTO' and session.rename_from is not None:
        session.rename_from = None

    handler = self._handlers.get(command)
    ...
```

Và trong `rnto()`:
```python
def rnto(self, session, arg):
    if not session.rename_from:
        return "503 Bad sequence of commands.\r\n"
    if not arg or not arg.strip():
        session.rename_from = None
        return "501 Syntax error in parameters.\r\n"
    try:
        result = self._fs(session).rename(session.rename_from, arg.strip())
        session.rename_from = None
        return "250 Rename successful.\r\n"
    except FilesystemOperationError as e:
        session.rename_from = None
        return self._fs_error_reply(e)
```

**Review and refinement:**
Đã tích hợp guard vào `dispatch()`. Thêm `session.rename_from = None` trong `ClientHandler.cleanup()`. Thêm 6 unit test: `RNFR`→`RNTO` thành công, `RNFR`→`CWD` reset state, `RNFR`→`RNTO` thiếu arg reset state, `RNFR`→`QUIT` reset state, `RNFR`→`RNTO` path traversal reset state, disconnect reset state. Tất cả pass.

---

## [07/08/2026] - ClientHandler Cleanup Đầy Đủ + Session ID (tuần 2.5)

**Exact prompt:**
> "`ClientHandler.cleanup()` hiện chỉ đóng TCP socket và unregister. Hãy cải tiến toàn diện:
> 1. Thêm `session_id` duy nhất cho mỗi session khi khởi tạo (dùng `uuid.uuid4()` hoặc atomic counter).
> 2. Thêm `Session.new_transfer_id()` trả transfer ID riêng cho mỗi lần transfer.
> 3. Sửa `cleanup()` thực hiện đúng thứ tự:
>    a. `transfer_manager.cancel(session)` — set cancel event.
>    b. Đóng `session.data_socket`.
>    c. Clear `session.data_host`, `session.data_port`, `session.data_mode`.
>    d. Clear `session.rename_from`, `session.transfer_cancel_event`, `session.current_transfer`.
>    e. Join `session.current_transfer` (worker thread) với timeout 5 giây.
>    f. Unregister khỏi server active-session registry.
>    g. Đóng TCP control socket.
> Đảm bảo QUIT/disconnect/shutdown không để lại thread, socket hoặc session stale."

**Raw GenAI output:**
AI sinh code đầy đủ cho `cleanup()` với `try/finally` ở mỗi bước để đảm bảo không bị block kể cả khi một bước fail:

```python
def cleanup(self):
    # 1. Cancel transfer
    try:
        if self.transfer_manager:
            self.transfer_manager.cancel(self.session)
    except Exception:
        pass
    # 2. Đóng data socket
    try:
        if self.session.data_socket:
            self.session.data_socket.close()
    except Exception:
        pass
    finally:
        self.session.data_socket = None
        self.session.data_host = None
        self.session.data_port = None
        self.session.data_mode = None
    # 3. Clear session state
    self.session.rename_from = None
    self.session.transfer_cancel_event = None
    # 4. Join worker thread
    worker = self.session.current_transfer
    if worker and worker.is_alive():
        worker.join(timeout=5)
    self.session.current_transfer = None
    # 5. Unregister
    try:
        self.server.unregister(self)
    except Exception:
        pass
    # 6. Đóng TCP socket
    try:
        self.conn.close()
    except Exception:
        pass
```

**Review and refinement:**
Đã tích hợp vào `server/client_handler.py`. Session ID dùng `str(uuid.uuid4())[:8]` cho ngắn gọn trong log. `Session.new_transfer_id()` dùng `f"T{self.session_id}-{next(self._transfer_counter)}"`. Thêm 4 unit test `TestCleanup`: xác nhận cancel được gọi, data socket bị đóng, worker thread được join, unregister được gọi. Tất cả pass.

---

## [07/08/2026] - Authentication Contract Rõ Ràng (tuần 2.5)

**Exact prompt:**
> "Authentication hiện tại dùng password hard-code `123456` và mọi username không rỗng đều hợp lệ. Hãy sửa:
> 1. Thay bằng dictionary `credentials` rõ ràng với các tài khoản: `admin`, `user`, `testuser`, `anonymous`.
> 2. `USER` mới phải reset `is_logged_in = False` và `rename_from = None` per RFC 959.
> 3. `PASS` gửi trước `USER` → `503 Login with USER first`.
> 4. Sai password → xóa `username = None`, yêu cầu `USER` mới.
> 5. `anonymous` login không cần password (hoặc password rỗng).
> 6. Disconnect/QUIT reset toàn bộ login state."

**Raw GenAI output:**
AI đề xuất:

```python
CREDENTIALS = {
    "admin":     "123456",
    "user":      "password",
    "testuser":  "test123",
    "anonymous": "",
}

def user(self, session, arg):
    if not arg or not arg.strip():
        return "501 Syntax error in parameters.\r\n"
    session.is_logged_in = False
    session.rename_from = None
    session.username = arg.strip()
    return "331 Password required.\r\n"

def password(self, session, arg):
    if not session.username:
        return "503 Login with USER first.\r\n"
    if session.is_logged_in:
        return "230 Already logged in.\r\n"
    expected = CREDENTIALS.get(session.username)
    if expected is None or (expected != "" and arg != expected):
        session.username = None
        return "530 Login incorrect.\r\n"
    session.is_logged_in = True
    return "230 User logged in.\r\n"
```

**Review and refinement:**
Đã tích hợp. `anonymous` login chấp nhận bất kỳ password (kể cả rỗng). Thêm 6 unit test: login đúng, sai password, `PASS` trước `USER`, `USER` mới reset login, `anonymous` không cần pass, disconnect reset state. Tất cả pass.

---

## [07/08/2026] - Argument Validation Table Chung (tuần 2.5)

**Exact prompt:**
> "Mỗi command handler tự kiểm tra tham số riêng và không nhất quán. Một số lệnh như `PASV`, `QUIT`, `NOOP` vẫn chấp nhận tham số thừa mà không báo lỗi. Hãy thiết kế một cơ chế validation chung:
> - Lệnh bắt buộc 1 tham số: `USER`, `PASS`, `CWD`, `MKD`, `RMD`, `DELE`, `RNFR`, `RNTO`, `TYPE`, `MODE`, `PORT`, `RETR`, `STOR`, `APPE`, `HASH` — thiếu → `501`.
> - Lệnh không nhận tham số: `QUIT`, `NOOP`, `PWD`, `CDUP`, `PASV`, `ABOR`, `HELP` — thừa → `501`.
> - Lệnh tham số tuỳ chọn: `STOU`, `LIST`, `NLST`, `STAT` — không kiểm tra.
> Áp dụng validation trước khi gọi handler, tập trung trong `dispatch()`."

**Raw GenAI output:**
AI đề xuất:

```python
REQUIRED_ARG = {'USER', 'PASS', 'CWD', 'MKD', 'RMD', 'DELE', 'RNFR',
                'RNTO', 'TYPE', 'MODE', 'PORT', 'RETR', 'STOR', 'APPE', 'HASH'}
NO_ARG       = {'QUIT', 'NOOP', 'PWD', 'CDUP', 'PASV', 'ABOR', 'HELP'}

def dispatch(self, session, command, arg):
    if command in REQUIRED_ARG and not (arg and arg.strip()):
        return "501 Syntax error in parameters.\r\n"
    if command in NO_ARG and arg and arg.strip():
        return "501 Syntax error in parameters.\r\n"
    ...
```

**Review and refinement:**
Đã tích hợp vào đầu `dispatch()`, trước guard reset `rename_from`. Thêm 14 unit test bao phủ toàn bộ hai nhóm: lệnh bắt buộc arg thiếu, lệnh không arg bị thừa. Xóa kiểm tra tham số trùng lặp bên trong từng handler. Tổng test sau bước này: 61 pass.

---

## [07/08/2026] - Test Suite Mở Rộng: TCP Framing, Lifecycle, Cleanup (tuần 2.5)

**Exact prompt:**
> "Cần bổ sung các test còn thiếu để phủ đầy đủ:
> 1. **TCP framing**: command bị chia qua hai `recv`, hai command trong một `recv`, UTF-8 lỗi, CRLF thừa/thiếu.
> 2. **Transfer lifecycle**: `150` xuất hiện trước `226`/`426`; `ABOR` trong lúc transfer đang chạy; data connection check.
> 3. **Cleanup assertion**: sau `cleanup()`, không còn worker thread alive, data socket còn mở, session field còn giá trị cũ.
> 4. **Session isolation**: thay đổi state session A không ảnh hưởng session B.
> 5. **Transfer ID**: mỗi lần `new_transfer_id()` trả ID khác nhau, không bị trùng giữa các session.
> Viết test bằng `unittest.mock.MagicMock` cho adapter và `threading.Event` cho cancel."

**Raw GenAI output:**
AI sinh file test mới `tests/test_transfer_manager.py` và class `TestRoleAValidationAndRDTAdapter` trong `tests/test_commands.py` với đầy đủ các test case nêu trên, dùng mock sender/receiver và mock filesystem.

**Review and refinement:**
Đã integrate. Một số mock cần chỉnh: `receiver.receive` phải trả `iter([b'chunk1', b'chunk2'])` thay vì list để giống production. `sender.send` mock trả `int` (số bytes). `threading.Event` dùng thật (không mock) để test cancel đúng. Kết quả cuối: **61 unit test pass 100%** trong `test_command_parser.py`, `test_session.py`, `test_commands.py`, `test_transfer_manager.py`.

---

## [09/08/2026] - Task A-F01: MODE Compliance & Limitation Review (Final Week)

**Exact prompt:**
> "Rà soát tuân thủ lệnh `MODE` theo yêu cầu §2.2 bài tập: (1) `MODE S` (Stream) phải hoạt động chuẩn và trả `200 Mode Stream`; (2) `MODE B` (Block) và `MODE C` (Compressed) không được báo thành công giả (không trả 200), mà phải trả mã `502 Mode not implemented` và ghi rõ limitation trung thực; (3) Thêm unit tests kiểm tra `MODE S/B/C`, tham số không hợp lệ, khi chưa đăng nhập và tính cô lập giữa các session; (4) Cập nhật tài liệu báo cáo kỹ thuật."

**Raw GenAI output:**
AI đề xuất phương án xử lý `mode_cmd` trong `CommandHandler`:

```python
def mode_cmd(self, arg, session):
    if not session.is_logged_in:
        return "530 Not logged in\r\n"
    if not arg:
        return "501 Missing argument\r\n"
    mode = arg.upper()
    if mode == "S":
        session.transfer_mode = "S"
        return "200 Mode Stream\r\n"
    elif mode in ("B", "C"):
        return "502 Mode not implemented\r\n"
    return "501 Invalid MODE\r\n"
```

Và thêm class `TestModeComplianceRoleA` kiểm thử các trường hợp `MODE S`, `MODE B`, `MODE C`, `MODE X`, chưa login và session isolation.

**Review and refinement:**
Đã xác nhận và tích hợp `TestModeComplianceRoleA` vào `tests/test_commands.py` (dòng 634). Cập nhật phần 4 trong `docs/report-parts/technical/04-control-channel.md` với bảng lệnh và giải thích lý do trả mã `502` cho `MODE B/C` theo đúng tinh thần báo cáo trung thực. Không thêm codec/framing nào ngoài yêu cầu đề — vì bảng §2.2 không có cột Level cho MODE, `502` trung thực tốt hơn trả `200` cho chức năng chưa có data-path. MODE không nhầm với Active/PASV (mode = cấu trúc byte stream trên data channel, Active/PASV = ai khởi tạo kết nối data).

**Verification:**
- `python3 -m pytest tests/test_commands.py -q` — `TestModeComplianceRoleA` 5 test pass: MODE S → 200, MODE B/C → 502, MODE X → 501, chưa login → 530, session isolation.
- Final Role A audit: `python3 -m pytest tests/test_command_parser.py tests/test_commands.py tests/test_session.py tests/test_threaded_server.py -q` — **63 passed in 5.71s**; full suite — **199 passed in 96.72s**; evidence `docs/evidence/final-week-rdt-gbn-verification.md`.

---

## [09/08/2026] - Task A-F02: 28-Command Compliance Matrix & Transfer Lifecycle (Final Week)

**Exact prompt:**
> "Lập bảng ma trận kiểm thử tuân thủ cho toàn bộ 28 lệnh FTP theo yêu cầu bài tập (§2.2): (1) Kiểm tra đủ 28 lệnh trong `CommandHandler`; (2) Xác nhận luồng chuỗi phản hồi transfer `150 -> 226/4xx` trên kênh TCP control và worker thread; (3) Bổ sung class test `TestCommandMatrix28RoleA` bảo đảm không lệnh nào bị bỏ sót; (4) Cập nhật phần 4 trong báo cáo kỹ thuật."

**Raw GenAI output:**
AI sinh danh sách 28 lệnh và ma trận test case trong `TestCommandMatrix28RoleA`, xác minh phản hồi lệnh `HELP` trả về `214` chứa đầy đủ danh sách lệnh hỗ trợ, các lệnh chưa hỗ trợ (như `SITE`) trả về `502`.

**Review and refinement:**
Đã tích hợp vào `tests/test_commands.py` (dòng 680) và hoàn thiện `docs/report-parts/technical/04-control-channel.md` mục 4.2 (bảng 28 lệnh với tham số + reply) và 4.4 (luồng `150 -> 226/4xx`, xử lý `ABOR`). Ma trận reply ghi rõ reply ba chữ số thực tế của từng lệnh; `150 -> 226` chỉ xuất hiện sau transfer thực, lỗi map đúng `425`/`426`/`450`/`550`; `LIST`/`NLST` trả text qua TCP (chỉ file payload đi UDP/RDT).

**Verification:**
- `TestCommandMatrix28RoleA`: đủ 28 lệnh `USER...ABOR`, `HELP` → `214`, lệnh ngoài đề (`SITE`) → `502`.
- Final Role A audit — **63 passed in 5.71s**; full WSL2 regression — **199 passed in 96.72s**; evidence `docs/evidence/final-week-rdt-gbn-verification.md`.

---
## [10/08/2026] - Functional MODE S/B/C (Final Week — Role A handoff)

**Exact prompt:**
> "Implement functional Stream/Block/Compressed transfer modes per `Project1_SocketProgramming_2026.md` §2.2 and RFC 959 §3.4, replacing the honest-but-limited `502` baseline. Scope: real bidirectional codecs, production-path integration with Role C filesystem/RDT, exact replies/state, failure handling and evidence."

**Raw GenAI output:**
- `common/mode_codec.py` — `normalize_mode`, `encode_chunks`/`decode_chunks` dispatcher, RFC-959 Block (`0x40` EOF descriptor + 2-byte big-endian count), FTP RLE Compressed (literal `0xxxxxxx`, repeated `10nnnnnn`, filler `11nnnnnn`, EOF `0x00 0x40`), streaming generators, `_batch_wire` to cap wire chunks at 1024 bytes.
- `server/command_handler.py` `mode_cmd` — `MODE S/B/C` → `200 Mode Stream/Block/Compressed`; invalid/missing → `501`; unauthenticated → `530`; updates only `session.transfer_mode`.
- `server/transfer_manager.py` — `TransferContext.transfer_mode`; encode before RDT send, decode after RDT receive; `STOR`/`APPE`/`STOU` keep atomic `.part` and shared locks; decode errors → `426` with no partial file.
- `client/ftp_client.py` — per-client `transfer_mode`, one-time `MODE` negotiation (`_negotiated_mode`), codec on send/receive.
- `common/rdt_sender.py`/`rdt_receiver.py` — progress reports logical (decoded) bytes so CLI never exceeds 100%; RDT wire layout unchanged.

**Review and refinement:**
Fixes during verification: block wire chunks batched to ≤1024; compressed literal-run tail corrected; `receive_chunks_rdt` progress fired before first yield so total is known; `TestModeComplianceRoleA` expanded with per-session client state.

**Verification:**
- `python3 -m pytest tests/test_mode_codec.py tests/test_commands.py -q` — **83 passed, 338 subtests**.
- `python3 -m pytest tests/test_transfer_manager.py -q` — **12 passed** (block/compressed decode on store, append, STOU, malformed→426 atomic, cancel và disconnect giữa block/run giữ file cũ, không để `.part`).
- `python3 -m pytest tests/test_rdt_fault_injection.py -q` — **19 passed, 11 subtests** (B/C payloads under loss/corruption/ACK-loss/duplicate/out-of-order).
- `python3 -m pytest tests/test_e2e_transfer.py -q` — **13 passed, 8 subtests** (PASV/ACTIVE × S/B/C SHA-256, STOU/APPE block, concurrent different-mode clients, progress ≤100%, server-stop mid-B-upload).
- Full `python3 -m pytest -q` — **256 passed, 357 subtests in 167.08s**.

---

## [10/08/2026] - Final verification, reliability hardening & report audit (Role A)

**Exact prompt:**
> "Kiểm tra lại toàn bộ evidence Role A MODE S/B/C (code locator + test log),
> audit checklist "Report mô tả đúng implementation cuối, không claim trước
> evidence", rồi viết báo cáo fix A/C và log GenAI. Dựa trên các prompt trước:
> implement functional S/B/C trên production path, hardening reliability
> (duplicate/out-of-order, cancel/disconnect mid-block, server-stop mid-upload),
> và cross-review evidence thật."

**Raw GenAI output:**
- Rerun toàn bộ test suites để xác nhận số liệu evidence (không đóng bằng
  static code review):
  - `test_mode_codec.py` + `test_commands.py` — **83 passed, 338 subtests** (0.27s).
  - `test_mode_codec.py` — **29 passed, 338 subtests** (0.12s).
  - `test_transfer_manager.py` — **12 passed** (0.06s).
  - `test_rdt_fault_injection.py` — **19 passed, 11 subtests** (71.99s).
  - `test_e2e_transfer.py` — **13 passed, 8 subtests** (77.20s).
  - Full `python3 -m pytest -q` — **256 passed, 357 subtests** (172.58s).
- Audit code locator bằng grep: `mode_codec.py` (`normalize_mode`,
  `encode_chunks`/`decode_chunks`, `block_encode`/`block_decode`,
  `compressed_encode`/`compressed_decode`, `WIRE_CHUNK_SIZE`, `_batch_wire`),
  `command_handler.py` `mode_cmd` (200/501/530, `session.transfer_mode`),
  `transfer_manager.py` `TransferContext.transfer_mode` encode-before-RDT/
  decode-after-RDT, `ftp_client.py` `_negotiated_mode`/`_ensure_transfer_mode`,
  `demo_transfer.py` `--transfer-mode`, `rdt_sender.py`/`rdt_receiver.py`
  progress logical bytes — tất cả đúng như evidence.
- Audit report: `docs/report.md` §8 Final Evidence table stale (chỉ 205 passed/
  103.08s, thiếu MODE row) → thêm row "MODE S/B/C functional codecs" với số thật,
  relabel 205 thành historical baseline; §9 numbers (135 passed/86.22s, 45 passed/
  67.09s) trace được về `final-week-rdt-gbn-verification.md`, `genai-log-c.md`,
  `genai-log-b.md`, `05-data-channel-rdt.md`; §12 limitations accurate.
- Đồng bộ số liệu cuối vào 9 docs (code-change-history, project-status,
  requirement-checklist, api-contract, report.md, report-parts 04/10/12,
  evidence, genai-log-a) và viết `docs/report-fix-a-c.md`.
- Đóng checklist item "Report mô tả đúng implementation cuối" (`final-code-fix-a-c.md:229`).

**Review and refinement:**
- "24 passed (C-FIX03)" là baseline lịch sử pre-MODE; re-run hiện tại của 4-file
  set đó = **39 passed, 8 subtests / 80.48s** vì transfer-manager 10→12 và e2e
  12→13 — không phải lỗi evidence.
- Các ô chờ B/C confirm (A-MODE06) và git release giữ nguyên unchecked theo
  nguyên tắc cross-review ở đầu file.

**Verification:**
- Full `python3 -m pytest -q` — **256 passed, 357 subtests, không failure**.
- Mọi số trong `docs/report-fix-a-c.md`, `docs/evidence/final-code-fix-verification.md`
  và §8 report.md đều là kết quả chạy thật.
- Còn pending: A+C production E2E matrix, B confirm RDT wire layout, C confirm
  filesystem/atomic cleanup, git release check.

---

## [10/08/2026] - Nhúng Evidence Screenshots vào Report §7 (Final Week)

**Exact prompt:**
> "Nhúng vào report `docs/report.md` §7 với caption đúng phạm vi:
> - Trong §7: dùng
>   `![Full regression — 199 passed](evidence/screenshots/01-full-pytest-199-passed.png)`
>   kèm figure caption "Full WSL2 regression passed; this verifies the integrated
>   suite."
> - Nhúng ảnh 02 dưới §7.1 hoặc §7.2.
> - Nhúng ảnh 03 và ảnh 04 dưới §7.3.
> - `final-lan-pasv.png` và `active-demo-success.png` có thể dùng bổ sung, nhưng
>   không thay thế ảnh 02–04."

**Raw GenAI output:**
AI đề xuất bố trí 4 ảnh theo thứ tự số: ảnh 01 đặt ngay đầu §7 làm bằng chứng
full regression; ảnh 02 đặt dưới §7.1 (kế bên LAN server excerpt) hoặc §7.2;
ảnh 03 và 04 đặt dưới §7.3; giữ 2 ảnh cũ làm bổ sung. Mỗi ảnh dùng block
Markdown `![alt](path)` + dòng `*Figure caption*`.

**Review and refinement:**
- Tên file thật khác prompt: screenshot full regression là
  `01-full-pytest-271-passed.png` hiển thị **271 passed** (sau production-review
  hardening), không phải `01-full-pytest-199-passed.png` (199 passed là baseline
  cũ pre-MODE). Đã dùng tên file thật và sửa alt text/caption thành
  **271 passed** cho khớp evidence và §8 report (full 271 passed + 357 subtests
  in 192.88s).
- Rename 2 file có khoảng trắng thừa đầu tên (` 01-full-pytest-271-passed.png`,
  ` 03-sha256-pasv-active.png`) → bỏ space để link Markdown sạch.
- Đường dẫn tương đối `evidence/screenshots/…` từ `docs/report.md` resolve đúng
  thư mục `docs/evidence/screenshots/`.
- Bố trí cuối: 01 đầu §7; 02 dưới §7.1 (lan-pasv-server-lifecycle kế bên LAN
  server excerpt); 03 (sha256-pasv-active) và 04 (three-pasv-clients) dưới §7.3;
  `final-lan-pasv.png` và `active-demo-success.png` giữ nguyên làm ảnh bổ sung.

**Verification:**
- Toàn bộ 6 link ảnh trong `docs/report.md` resolve tới file tồn tại trong
  `docs/evidence/screenshots/`.
- Số "271 passed" khớp với §8 Final Evidence table và
  `docs/evidence/role-a-production-review-2026-08-10.md`.
- Danh sách chi tiết được ghi trong `docs/screenshots.md`.

---
