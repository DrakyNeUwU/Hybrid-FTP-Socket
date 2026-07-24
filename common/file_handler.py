"""
file_handler.py — Module đọc/ghi file binary an toàn

=== FILE NÀY GIẢI QUYẾT GÌ? ===
Cung cấp tất cả thao tác file cho hệ thống Hybrid FTP:
  - Đọc file → bytes (để Role B gửi qua UDP)
  - Ghi bytes → file (khi nhận file từ UDP)
  - Chia file thành chunks nhỏ (vì UDP không gửi cả file 1 lần)
  - Ráp chunks lại thành file hoàn chỉnh
  - Tính hash MD5/SHA-256 để verify file sau khi truyền

=== KẾT NỐI VỚI FILE NÀO? ===
  - server/threaded_server.py  → gọi khi xử lý RETR (download) / STOR (upload)
  - Role B's RDT module        → lấy chunks để gửi, nhận chunks để ráp
  - common/dir_manager.py      → dir_manager validate path trước, rồi gọi file_handler để đọc/ghi

=== XOÁ FILE NÀY THÌ GÌ HỎNG? ===
  - Toàn bộ lệnh RETR, STOR, STOU, APPE không hoạt động (không thể đọc/ghi file)
  - Lệnh HASH không hoạt động (không tính được hash)
  - Lệnh SIZE không hoạt động (không lấy được kích thước file)
"""

import os
import hashlib


# ============================================================
# CONSTANTS
# ============================================================

# Kích thước mỗi chunk khi chia file để gửi qua UDP.
# Tại sao 1024?
#   - UDP max payload = 65,507 bytes, nhưng thực tế nên < MTU (1500 bytes)
#   - Trừ đi IP header (20B) + UDP header (8B) + RDTHeader (~20-30B) ≈ còn ~1450B
#   - Chọn 1024 (2^10) — số tròn, an toàn, dễ tính toán, dễ debug
#   - Role B có thể override bằng cách truyền chunk_size khác khi gọi hàm
DEFAULT_CHUNK_SIZE = 1024


# ============================================================
# ĐỌC FILE
# ============================================================

def read_file(path: str) -> bytes:
    """
    Đọc toàn bộ file dạng binary.

    Cách hoạt động:
      1. Mở file ở mode "rb" (read binary)
         - "r" = read, "b" = binary
         - Nếu dùng "r" (không có "b"), Python sẽ tự chuyển đổi line endings
           (\\n ↔ \\r\\n trên Windows) → làm hỏng file binary (ảnh, zip...)
      2. Đọc toàn bộ nội dung vào bộ nhớ
      3. Trả về object kiểu `bytes`

    Khi nào dùng:
      - File nhỏ (< vài MB) mà muốn lấy toàn bộ nội dung 1 lần
      - Khi cần hash toàn bộ file (nhưng compute_hash hiệu quả hơn cho file lớn)

    Khi nào KHÔNG nên dùng:
      - File rất lớn (hàng trăm MB) → dùng read_file_chunks() thay vì load hết vào RAM

    Args:
        path: Đường dẫn tuyệt đối đến file cần đọc

    Returns:
        bytes: Nội dung file dạng binary

    Raises:
        FileNotFoundError: Nếu file không tồn tại
        PermissionError: Nếu không có quyền đọc
        IsADirectoryError: Nếu path trỏ đến thư mục, không phải file
    """
    with open(path, "rb") as f:
        return f.read()
    # Giải thích "with":
    #   - Tự động đóng file khi thoát khối with (kể cả khi có exception)
    #   - Nếu dùng f = open(...) mà quên f.close() → rò rỉ file descriptor
    #   - Mỗi OS giới hạn số file descriptor mở đồng thời (~1024 trên Linux)


def read_file_chunks(path: str, chunk_size: int = DEFAULT_CHUNK_SIZE):
    """
    Generator: đọc file theo từng chunk, yield từng mảnh bytes.

    Cách hoạt động:
      1. Mở file binary
      2. Đọc `chunk_size` bytes mỗi lần (mặc định 1024)
      3. Yield chunk đó ra ngoài (trả tạm, chưa đọc tiếp)
      4. Khi caller gọi next(), đọc chunk tiếp theo
      5. Lặp cho đến khi f.read() trả về b"" (hết file)

    Tại sao dùng generator (yield) thay vì list?
      - Giả sử file 100MB, chunk_size = 1024:
        - List: tạo list 100,000 phần tử → chiếm 100MB RAM + overhead
        - Generator: chỉ giữ 1 chunk trong RAM tại 1 thời điểm → ~1KB RAM
      - Rất quan trọng khi server phục vụ nhiều client đồng thời (mỗi client
        đang transfer 1 file → nếu dùng list, 10 client × 100MB = 1GB RAM)

    Ví dụ sử dụng:
      for chunk in read_file_chunks("photo.jpg"):
          rdt_sender.send(chunk)   # Role B gửi từng chunk qua UDP

    Args:
        path: Đường dẫn tuyệt đối đến file
        chunk_size: Kích thước mỗi mảnh (bytes). Mặc định 1024.

    Yields:
        bytes: Từng mảnh dữ liệu, mảnh cuối có thể < chunk_size
    """
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            # f.read(n) đọc tối đa n bytes
            # Trả về b"" (bytes rỗng) khi hết file
            if not chunk:
                break
            yield chunk
            # yield: trả chunk ra ngoài và "tạm dừng" hàm tại đây
            # Khi caller gọi next(), hàm chạy tiếp từ dòng while True


# ============================================================
# GHI FILE
# ============================================================

def write_file(path: str, data: bytes) -> int:
    """
    Ghi dữ liệu binary ra file (ghi đè nếu file đã tồn tại).

    Cách hoạt động:
      1. Tạo thư mục cha nếu chưa tồn tại (exist_ok=True → không lỗi nếu đã có)
      2. Mở file ở mode "wb" (write binary)
         - "w" = write (tạo mới hoặc ghi đè)
         - "b" = binary (không chuyển đổi line endings)
      3. Ghi toàn bộ data vào file
      4. Trả về số bytes đã ghi

    Khi nào dùng:
      - Khi đã có toàn bộ nội dung file trong bộ nhớ
      - File nhỏ, nhận xong 1 lần

    Args:
        path: Đường dẫn đến file cần ghi
        data: Dữ liệu binary cần ghi

    Returns:
        int: Số bytes đã ghi
    """
    # Tạo thư mục cha nếu chưa có
    # Ví dụ: path = "/srv/ftp/docs/report.pdf"
    #   → os.path.dirname() = "/srv/ftp/docs"
    #   → makedirs tạo /srv → /srv/ftp → /srv/ftp/docs nếu chưa tồn tại
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(path, "wb") as f:
        return f.write(data)


def write_file_from_chunks(path: str, chunks) -> int:
    """
    Nhận iterable of bytes, ghi tuần tự ra file.

    Cách hoạt động:
      1. Tạo thư mục cha nếu cần
      2. Mở file ở mode "wb"
      3. Duyệt qua từng chunk, ghi nối tiếp (append) vào file
      4. Trả về tổng số bytes đã ghi

    Tại sao cần hàm riêng (không gọi write_file nhiều lần)?
      - write_file mở mode "wb" → mỗi lần gọi sẽ XOÁ file cũ rồi ghi mới
      - Hàm này chỉ mở file 1 lần, ghi nối tiếp → đúng thứ tự

    Ví dụ sử dụng (khi Role B nhận chunks qua UDP):
      chunks_received = []
      while not transfer_done:
          chunk = rdt_receiver.receive()
          chunks_received.append(chunk)
      write_file_from_chunks("downloaded.pdf", chunks_received)

    Args:
        path: Đường dẫn file đích
        chunks: Iterable (list, generator...) of bytes

    Returns:
        int: Tổng số bytes đã ghi
    """
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    total_written = 0
    with open(path, "wb") as f:
        for chunk in chunks:
            written = f.write(chunk)
            total_written += written
    return total_written


def append_to_file(path: str, data: bytes) -> int:
    """
    Ghi nối thêm (append) dữ liệu vào cuối file. Tạo file nếu chưa tồn tại.

    Dùng cho lệnh FTP APPE (Append):
      - Nếu file đã có 100 bytes, append thêm 50 bytes → file có 150 bytes
      - Khác với write_file: write_file xoá sạch file cũ rồi ghi mới

    Mode "ab":
      - "a" = append (ghi thêm vào cuối, không xoá nội dung cũ)
      - "b" = binary

    Args:
        path: Đường dẫn file
        data: Dữ liệu cần ghi thêm

    Returns:
        int: Số bytes đã ghi thêm
    """
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(path, "ab") as f:
        return f.write(data)


# ============================================================
# HASH — XÁC MINH TÍNH TOÀN VẸN DỮ LIỆU
# ============================================================

def compute_hash(path: str, algorithm: str = "sha256") -> str:
    """
    Tính hash (băm) của file để kiểm tra tính toàn vẹn sau khi truyền.

    Cách hoạt động:
      1. Tạo object hash theo algorithm (md5 hoặc sha256)
      2. Đọc file theo chunks (không load hết vào RAM)
      3. Feed từng chunk vào hash object (update())
      4. Trả về hex digest (chuỗi hex, ví dụ: "a3f2e8...b9c1")

    Tại sao đọc theo chunk thay vì hash(read_file(path))?
      - File 1GB → load hết 1GB vào RAM chỉ để hash → lãng phí
      - hashlib.update() có thể feed dữ liệu nhiều lần → kết quả hash giống nhau
      - Chứng minh: hash(A+B+C) == h.update(A); h.update(B); h.update(C)

    Ví dụ sử dụng (lệnh HASH):
      hash_before = compute_hash("original.pdf")     # Trước khi gửi
      # ... truyền qua UDP ...
      hash_after = compute_hash("received.pdf")       # Sau khi nhận
      if hash_before == hash_after:
          print("226 File integrity verified")
      else:
          print("451 Transfer failed, hash mismatch")

    Args:
        path: Đường dẫn file
        algorithm: "md5" hoặc "sha256" (mặc định "sha256")

    Returns:
        str: Chuỗi hex digest (ví dụ: "e3b0c442...")

    Raises:
        ValueError: Nếu algorithm không được hỗ trợ
        FileNotFoundError: Nếu file không tồn tại
    """
    # Kiểm tra algorithm hợp lệ
    supported = ("md5", "sha256")
    if algorithm not in supported:
        raise ValueError(
            f"Unsupported hash algorithm: '{algorithm}'. "
            f"Supported: {supported}"
        )

    # hashlib.new() tạo hash object theo tên algorithm
    h = hashlib.new(algorithm)

    # Đọc file theo chunks và feed vào hash
    # Dùng read_file_chunks() của chính module này → tái sử dụng code
    for chunk in read_file_chunks(path):
        h.update(chunk)
        # update() nhận thêm dữ liệu vào hash đang tính
        # Có thể gọi nhiều lần, kết quả cuối = hash của toàn bộ dữ liệu

    return h.hexdigest()
    # hexdigest(): trả chuỗi hex (dễ đọc, dễ so sánh, dễ truyền qua TCP)
    # digest(): trả bytes (compact hơn nhưng khó đọc)


# ============================================================
# THÔNG TIN FILE
# ============================================================

def get_file_size(path: str) -> int:
    """
    Trả về kích thước file tính bằng bytes.

    Dùng cho lệnh FTP SIZE:
      Client gửi: SIZE report.pdf
      Server trả: 213 4096      (4096 bytes)

    Tại sao dùng os.path.getsize() thay vì len(read_file())?
      - os.path.getsize() chỉ đọc metadata từ filesystem → O(1), rất nhanh
      - len(read_file()) phải đọc toàn bộ file vào RAM → O(n), chậm và tốn RAM

    Args:
        path: Đường dẫn file

    Returns:
        int: Kích thước file (bytes)

    Raises:
        FileNotFoundError: File không tồn tại
        OSError: Không thể truy cập file
    """
    return os.path.getsize(path)


def file_exists(path: str) -> bool:
    """
    Kiểm tra file có tồn tại và là file (không phải thư mục).

    Dùng trước khi thực hiện RETR/DELE/SIZE... để trả reply code phù hợp:
      - Tồn tại → tiếp tục xử lý
      - Không tồn tại → 550 File unavailable

    Args:
        path: Đường dẫn cần kiểm tra

    Returns:
        bool: True nếu path tồn tại và là file
    """
    return os.path.isfile(path)
