# GenAI Usage Log — Role C (Khánh - Leader)

---

## 26/07/2026 — File Handler Module (`common/file_handler.py`)

**Prompt:**
> "Viết module đọc/ghi file binary an toàn trong Python dùng cho dự án FTP. Cần chia nhỏ file thành chunks 1024 bytes bằng generator, ráp chunks thành file, ghi đè, append file và tính hash SHA-256/MD5 của file."

**Raw GenAI Output:**
Gợi ý sử dụng `open(path, 'r')` kết hợp với `hashlib.sha256(f.read()).hexdigest()` cho file nhỏ và dùng `os.path.abspath()` để kiểm tra đường dẫn.

**Refinement & Auditing:**
- **Phát hiện lỗi:** Sử dụng mode `'r'` (text mode) trên Windows khiến ký tự `\r\n` bị tự động biến đổi thành `\n`, làm hỏng dữ liệu file binary (ảnh, zip, mp4).
- **Khắc phục:** Sửa bắt buộc toàn bộ sang binary mode (`'rb'`, `'wb'`, `'ab'`).
- **Tối ưu RAM:** Đọc hash bằng `hashlib.sha256(f.read())` nguyên file vào RAM là nguy hiểm nếu file lớn (1GB+). Đã tự refactor lại hàm `compute_hash` đọc theo từng chunk 1024 bytes kết hợp với `h.update(chunk)` giúp tiết kiệm RAM (chỉ tốn ~1KB RAM tại mọi thời điểm).

---

## 27/07/2026 — Directory Manager & Anti-Path Traversal (`common/dir_manager.py`)

**Prompt:**
> "Viết hàm Python kiểm tra an toàn một đường dẫn đầu vào từ Client để tránh lỗ hổng Path Traversal (`../../etc/passwd`). Hàm cần kiểm tra đường dẫn đó có nằm trong thư mục gốc FTP (sandbox) hay không."

**Raw GenAI Output:**
```python
def validate_path(base, target):
    return os.path.abspath(target).startswith(os.path.abspath(base))
```

**Refinement & Auditing:**
- **Phát hiện lỗi 1 (Symlink Trap):** `abspath()` chỉ nối chuỗi mà KHÔNG giải mã Symbolic Link (Symlink). Nếu hacker tạo một symlink `link -> /etc`, `abspath` vẫn tưởng nó nằm trong `base`. Đã đổi sang `os.path.realpath()` để resolve cả symlink và `..`.
- **Phát hiện lỗi 2 (False Positive String Prefix):** Nếu `base = "/srv/ftp"`, `target = "/srv/ftp_backup"`, hàm `startswith` trả về `True` (SAI hoàn toàn vì `ftp_backup` là thư mục khác!).
- **Khắc phục:** Thêm ký tự `os.sep` (`/` hoặc `\`) vào cuối `real_base` (`real_base + os.sep`), giúp phân định chính xác ranh giới thư mục.
- **Tối ưu hiệu năng:** Dùng `os.scandir()` thay vì `os.listdir()` trong hàm `list_directory()` giúp giảm số lượng system calls (syscalls) từ O(N) xuống O(1) do `DirEntry` đã lưu sẵn metadata `stat`.

---

## 28/07/2026 — Multi-Threaded TCP Server (`server/threaded_server.py`)

**Prompt:**
> "Viết socket server đa luồng bằng Python (threading). Server cần lắng nghe kết nối, tạo thread riêng cho mỗi client, theo dõi danh sách active clients thread-safe và có cơ chế stop server không bị dính treo."

**Raw GenAI Output:**
Tạo class kế thừa `threading.Thread`, dùng vòng lặp `while True: client, addr = server.accept()` không có timeout.

**Refinement & Auditing:**
- **Phát hiện lỗi:** Hàm `accept()` và `recv()` là blocking call nếu không có timeout. Khi gọi `server.stop()`, server socket bị đóng nhưng luồng chính vẫn đứng chờ `accept()` dẫn đến treo test.
- **Khắc phục:** Thêm `server_socket.settimeout(0.5)` và `client_socket.settimeout(0.5)`. Nhờ có timeout 0.5s, hàm `accept()` và `recv()` sẽ định kỳ nhả ngắt để kiểm tra cờ `is_running`, giúp ngắt kết nối an toàn (Graceful Shutdown).
- **Bổ sung Thread-safety:** Thêm `threading.Lock()` cho danh sách `active_clients` và hàm `safe_log()` để tránh xung đột ghi chung giữa các thread.

---

## 30/07/2026 — CLI Display Module (`client/cli_display.py`)

**Prompt:**
> "Viết module hiển thị CLI đẹp bằng Python: format dung lượng bytes ra KB/MB/GB, thanh tiến trình transfer bar dạng `[████░░░░] 50%` và bảng danh sách thư mục."

**Refinement & Auditing:**
- Tự thêm hàm `math.log(bytes, 1024)` để tự động chọn đơn vị `B`, `KB`, `MB`, `GB` phù hợp.
- Viết 6 unit tests kiểm tra độ rộng ký tự `█` và `░` của thanh tiến trình để không bị xô lệch trên các loại terminal khác nhau.
