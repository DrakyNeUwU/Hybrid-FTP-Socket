# GenAI Usage Log — Role B

> Ghi lại toàn bộ các lần dùng AI trong quá trình thực hiện Role B (UDP Data Channel & RDT Protocol).
> Format: Prompt chính xác → Raw output (AI làm gì) → Refinement (bổ sung/sửa lại thủ công).

---

## 2026-08-06 — Đọc yêu cầu Role B và lên workflow (Phiên 0)

**Prompt:**
> "đọc file tuan-2.5-fix.md cho tôi biết nhiệm vụ role B, cung cap workflow ro rang"

**Raw output:**
AI đọc `tuan-2.5-fix.md` và phân tích nhiệm vụ Role B gồm:
- Thiết lập RDT Contract: `RDTHeader`, network byte order, chunk size, timeout, retry limit, flags (`START`, `DATA`, `ACK`, `FIN`, `ABORT`).
- Hiện thực Sender/Receiver: Stop-and-Wait cơ bản, timeout, retransmit, ACK validation.
- Tích hợp với `TransferManager` qua `api-contract.md`.
- Black-box testing và documentation.

AI đưa ra workflow tuần tự 6 bước (RDTHeader → Sender → Receiver → Adapter → Tests → Docs).

**Refinement:**
- Workflow chỉ là định hướng, chưa có implementation. Team tự quyết định thứ tự ưu tiên fix theo lỗi thực tế.

---

## 2026-08-07 — Bổ sung UDP Peer Verification & transfer_id (Phiên 1 — sơ khai)

**Prompt:**
> "co hay giup toi" (trong context đọc `tuan-2.5-fix.md` để tìm lỗi)
> "o loi dau tien, timeout toi muon chinh la 1 giay"
> "giai thich them ve transfer_id trong RDTHeader"
> "them transfer_id vao file RDTHeader giup toi"
> "chi toi hoan thien buoc nay • Khi nhận ACK, kiểm tra xem ack_header.transfer_id có khớp với transfer_id hiện tại không."

**Raw output:**
1. **Peer Locking (Receiver):** AI thêm biến `peer_addr` vào `rdt_receiver.py` để lưu `(IP, Port)` của gói đầu tiên hợp lệ. Các gói từ địa chỉ khác bị drop với log `[Security]`.
2. **ACK Source Verification (Sender):** AI thêm resolve IP đích và so khớp nguồn ACK trước khi accept.
3. **Timeout:** Sửa `udp_socket.settimeout(1.0)`, thêm biến `timeout_count` để đếm timeout liên tiếp; sau 10 lần timeout → thoát an toàn.
4. **Giải thích transfer_id:** AI giải thích vai trò `transfer_id` trong môi trường multi-client UDP (tránh nhầm phiên, phân biệt retransmit vs new transfer).
5. **Thêm transfer_id vào header:** Đổi format từ `"!IIHIH"` (16 bytes) → `"!IIIHIH"` (20 bytes); cập nhật constructor và `deserialize()`.
6. **ACK validation transfer_id:** Sender so khớp `ack_header.transfer_id == transfer_id` khi nhận ACK.

**Files changed:** `common/RDTHeader.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`

**Refinement:**
- Format string `"!IIIHIH"` sau này được kiểm tra lại: `I I I H I H` = 4+4+4+2+4+2 = 20 bytes, đúng. Không cần sửa.
- Peer locking từ gói đầu tiên bất kỳ sau này được sửa lại: chỉ lock sau gói START/DATA hợp lệ (fix B-R5 phiên sau).

---

## 2026-08-07 — Bug Audit và Fix (Phiên 2)

**Prompt:**
> "fix cac loi uu tien roi doc cac file lien quan toi role B, tổng hợp lại các lỗi còn mắc phải"
> "fix file trước đọc file"

**Raw output:**
AI audit toàn bộ: `docs/api-contract.md`, `common/RDTHeader.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`, `server/transfer_manager.py`, `tests/test_rdt.py`, `tests/test_rdt_fault_injection.py`. Phát hiện và tạo artifact `role_b_bug_report.md` với 15 lỗi (B-01 đến B-15):

| # | Lỗi | Ưu tiên |
|---|---|---|
| B-01 | Không có `RDTSenderAdapter`/`RDTReceiverAdapter` theo api-contract §3 | Cao |
| B-02 | Adapter không dùng `getattr(context, field, default)` → crash khi field thiếu | Cao |
| B-04 | `receive_file_rdt` tự đóng socket → caller mất socket | Cao |
| B-05 | `receive_file_rdt` dùng `list()` → load cả file vào RAM | Trung bình |
| B-06 | `send_chunks_rdt` không detect FIN mà không load cả iterator | Trung bình |
| B-07 | Test dùng boolean simulation giả, không test production code | Cao |
| B-08 | `recvfrom(65535)` quá lớn, không khớp với chunk size thực tế | Thấp |
| B-09 | START packet không mang file size → receiver không biết total bytes | Cao |
| B-11 | `NetworkProxy` dùng `last_client_addr` → race condition trong multi-thread | Cao |

**Fixes thực hiện:**

| # | Fix | AI thực hiện |
|---|---|---|
| B-01 | Tạo `RDTSenderAdapter` / `RDTReceiverAdapter` conform api-contract §3 | ✓ |
| B-02 | Adapter dùng `getattr(context, field, default)` | ✓ |
| B-04 | Xóa `udp_socket.close()` khỏi `receive_file_rdt`; comment rõ caller chịu trách nhiệm | ✓ |
| B-05 | `receive_file_rdt` streaming với generator trực tiếp | ✓ |
| B-06 | `send_chunks_rdt` dùng lookahead-1 iterator (`_lookahead`) | ✓ |
| B-07 | Viết lại `test_rdt.py` với real socket unit tests | ✓ |
| B-11 | `NetworkProxy` dùng `dict[port → addr]` thay `last_client_addr` | ✓ |

**Files changed:** `common/RDTHeader.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`, `tests/test_rdt.py`, `tests/test_rdt_fault_injection.py`

**Refinement:**
- AI tạo `compute_checksum` với format string `"!IIIH H"` (có space thừa) → `struct.error`. Tự sửa thành `"!IIIHI"`.
- B-03 (transfer_id UUID 16-byte) và B-12/B-13 (documentation) ghi nhận là lỗi nhưng chưa xử lý hết phiên này.
- AI không thể chạy pytest (Python chưa cài trong runner) → test output chưa có; cần chạy tay.

---

## 2026-08-07 — Tiếp tục fix (Phiên 3)

**Prompt:**
> "tiếp tục fix"

**Raw output:**
AI đọc transcript phiên trước và artifact `role_b_bug_report.md`. Xác định B-08, B-09, B-12, B-13 còn thiếu:

- **B-08:** Fix `recvfrom` buffer: `65535` → `_RECV_BUF = RDTHeader.size + 1024 + 64 = 1108 bytes`.
- **B-09:** Implement `_send_start()` trong `rdt_sender.py`: gửi payload 8 bytes chứa `total_bytes` với cờ `FLAG_START`. Receiver trích xuất `total_bytes` để tính `progress_cb`.
- **B-12 & B-13:** Điền toàn bộ `docs/role-b-week-2.md` và `docs/genai-log-b.md`.

**Files changed:** `common/rdt_sender.py`, `common/rdt_receiver.py`, `docs/role-b-week-2.md`, `docs/genai-log-b.md`

**Refinement:**
- START packet là best-effort (chưa có ACK handshake) — nếu mất thì receiver không biết `total_bytes`, nhưng vẫn nhận DATA bình thường. Acceptable cho thời điểm đó; cần nâng cấp sau.
- `_RECV_BUF = 1108` bytes cứng; nên parameterize theo `chunk_size` từ `TransferContext` trong future.

---

## 2026-08-07 — Deep bug fix: critical protocol issues (Phiên 4)

**Prompt:**
> "đọc file tuan-2.5-fix.md rồi đọc các file liên quan tới role B, đưa ra các lỗi"
> "đưa câu lệnh để tôi compile các file này"

**Raw output:**
AI phân tích `tuan-2.5-fix.md` và toàn bộ Role B source/test files. Tạo artifact `role_b_bugs.md` với 7 lỗi nghiêm trọng blocking exit gate:

| # | Lỗi | File | Dòng |
|---|---|---|---|
| B-S1 | Sender ignore `data_socket` từ TransferManager, tự tạo socket → ABOR không hoạt động | `rdt_sender.py` | 116 |
| B-S4 | ACK checksum không được validate; `header.length != 0` không bị reject | `rdt_sender.py` | — |
| B-R1 | `max_timeouts = int(timeout_seconds)` → khi `timeout_seconds=1.0` → `max_timeouts=1` → abort sau 1s | `rdt_receiver.py` | 64-66 |
| B-R5 | Peer lock từ gói đầu tiên bất kỳ thay vì từ START/DATA hợp lệ | `rdt_receiver.py` | 132-136 |
| B-R6 | `_fin_grace()` dùng `break` thay `continue` → thoát sớm → sender retry exhaustion | `rdt_receiver.py` | 310 |
| B-S8 | START payload endianness: `<Q` (little-endian) vs `!Q` (big-endian) mismatch | `rdt_sender.py` | — |
| Test | Port tĩnh gây conflict khi chạy song song | `test_rdt.py` | — |

**AI thực hiện các fix:**
- `common/rdt_sender.py`: Sử dụng `data_socket` từ `TransferContext`; validate ACK checksum và length; dùng resolved IP cho ABORT; chuẩn hóa START payload sang big-endian `!Q`.
- `common/rdt_receiver.py`: Fix `max_timeouts` tính đúng; validate length gói nhận; validate checksum START; lock peer sau START hợp lệ; đổi `break` → `continue` trong `_fin_grace`.
- `tests/test_rdt.py` & `tests/test_rdt_fault_injection.py`: Chuyển port static → dynamic (`port=0`); thêm test ACK loss và cancellation.

**Lệnh verify cú pháp (AI đề xuất):**
```bash
python -c "import common.rdt_sender; import common.rdt_receiver; print('OK')"
python -m unittest tests.test_rdt tests.test_rdt_fault_injection -v
```

**Files changed:** `common/rdt_sender.py`, `common/rdt_receiver.py`, `tests/test_rdt.py`, `tests/test_rdt_fault_injection.py`

**Refinement:**
- Fix B-R6 (`break` → `continue`) là critical nhất: đây là nguyên nhân gốc khiến `test_loss_and_corruption_recovery` fail (sender exhausts retry ở FIN packet cuối).
- Dynamic port giúp test không flaky hoặc conflict khi chạy song song.
- Chuyển từ mock sang production adapter tăng độ tin cậy kiểm thử.

---

## 2026-08-09 — Black-box Testing (Phiên 5)

**Prompt:**
> "đọc file test_rdt.py để xây dựng black-box testing tiếp theo"
> "dựa vào file test_rdt.py, xây dựng black-box testing phù hợp"
> "thêm phần black-box testing vào file test_rdt.py"

**Raw output:**
AI đọc và phân tích cấu trúc `tests/test_rdt.py`. Đề xuất và implement 4 kịch bản black-box mới cho `TestRDTProtocolLogic`:

1. **`test_receiver_ignores_different_transfer_id`** — Gửi gói có `transfer_id` sai sau START; receiver phải bỏ qua mà không crash hoặc nhận nhầm.
2. **`test_receiver_aborts_on_abort_packet`** — Gửi gói `FLAG_ABORT`; receiver phải kết thúc transfer với exception/error không phải treo.
3. **`test_receiver_graceful_fin_ack_retransmission`** — Gửi `FLAG_FIN` trùng lặp trong grace period; receiver phải re-ACK lại FIN mà không reset state.
4. **`test_receiver_drops_invalid_length_packet`** — Gửi gói có `header.length` khác actual payload size; receiver phải drop và không ghi dữ liệu lỗi.

**Files changed:** `tests/test_rdt.py`

**Refinement:**
- Đảm bảo 4 test mới không thay đổi logic cũ; chỉ thêm sau `TestRDTProtocolLogic`.
- Chạy toàn bộ suite: **31/31 tests pass** trên môi trường cục bộ sau khi thêm.

---

## 2026-08-09 — Hướng dẫn kiểm tra gói START (Phiên 6)

**Prompt:**
> "hướng dẫn thực hiện Kiểm tra xem gói START có được ACK và retry hữu hạn theo thiết kế của C-F01 hay không"

**Raw output:**
AI phân tích mã nguồn và cung cấp hướng dẫn hai chiều:

**Phân tích tĩnh:**
- `common/rdt_sender.py` hàm `_send_start_with_ack` (dòng ~260): vòng lặp `for attempt in range(1, retry_limit + 1)`, gửi gói `FLAG_START | seq_num=0`, chờ ACK với `sock.recvfrom`, kiểm tra `_valid_ack(ack_hdr, transfer_id)` yêu cầu `ack_num == 0`. Nếu hết retry → raise `RuntimeError`.
- `common/rdt_receiver.py` dòng ~106: xử lý cờ `FLAG_START`, kiểm tra `seq_num == 0`, extract `total_bytes` từ payload, gửi ACK `ack_num=0` qua `_send_ack`.

**Phân tích động (test):**
- `test_start_ack_loss_retries_before_data_window`: mô phỏng mất ACK đầu của START; sender retry và thành công sau đó.
- `test_max_retry_limit_raises_runtime_error`: mô phỏng peer không phản hồi; sau `retry_limit` lần → `RuntimeError`.

**Lệnh chạy:**
```bash
py -m pytest tests/test_rdt.py::TestRDTProtocolLogic::test_start_ack_loss_retries_before_data_window tests/test_rdt.py::TestRDTProtocolLogic::test_max_retry_limit_raises_runtime_error
```

**Kết quả:** `2 passed in 0.27s`

**Refinement:**
- Lần đầu dùng `-k` với tên hàm có `\n` → pytest báo `ERROR: Wrong expression`. Sửa thành dùng `::ClassName::method` syntax.
- Khi chạy 2 test riêng → `2 passed, 29 deselected`: 29 items "deselected" là bình thường (pytest filter, không phải fail).

---

## 2026-08-09 — Final RDT Verification (Phiên 7)

**Prompt:**
> "kiểm tra lại toàn bộ role B sau khi đã sửa và ghi lại evidence cho report"

**Raw output:**
AI đối chiếu lại implementation với planning và tài liệu Role B, sau đó đề xuất cập nhật draft báo cáo phần UDP/RDT. Các module được kiểm tra:
- `common/RDTHeader.py`: 20-byte header `!IIIHIH`, validate flags, validate length.
- `common/rdt_sender.py`: `_send_start_with_ack`, Go-Back-N window 4, FIN retry, ABORT.
- `common/rdt_receiver.py`: START ACK, cumulative ACK, `_fin_grace`, peer lock.
- `tests/test_rdt.py` và `tests/test_rdt_fault_injection.py`.

**Verification thực tế:**
```bash
python3 -m pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q
```
**Kết quả: 45 passed in 67.09s**

**Report sections được thêm (AI hỗ trợ):**
- §2.3: Bảng 20-byte RDT Header (`transfer_id`, `sequence`, `acknowledgement`, `flags`, `payload_length`, `checksum`) + định nghĩa flags.
- §3.6: Mermaid state diagrams cho RDT Sender (Go-Back-N window 4) và Receiver (`_fin_grace`).
- §5.2: Self-assessment Role B (protocol integrity, START handshake, GBN, CRC-32, FIN grace).
- §7.3: Embedded test output 45 passed cho fault-injection evidence.

**Files changed:** `docs/report.md`, `docs/genai-log-b.md`, `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md`

**Refinement:**
- Dùng `python3 -m pytest` thay vì `pytest` để tránh nhầm môi trường Python trên WSL2.
- Evidence 45 passed là bằng chứng chính cho B-F01 và C-F01; ghi rõ ngày chạy và lệnh chạy.
- Full regression: `python3 -m pytest -q` → **199 passed in 96.72s**.

---

## 2026-08-10 — Hoàn thiện report §2.2 và §7 (Phiên 8)

**Prompt:**
> "check file tuan-cuoi-ngay-tai-phan-chia.md xem role B còn làm thiếu các task nào thì hoàn thiện, sau khi hoàn thành check vào file"
> "bổ sung file genai của role B theo format dựa vào dữ liệu lịch sử trò chuyện với AI"

**Raw output:**
AI đọc `tuan-cuoi-ngay-tai-phan-chia.md`, phân tích checklist B-F02 còn thiếu. Xác định 2 task kỹ thuật mà Role B có thể tự hoàn thiện:

1. **§2.2 Session Structure:** AI đọc `server/session.py`, xác nhận struct thực tế có 16 attributes (thay vì 3 field cũ). Cập nhật `docs/report.md` với class definition đầy đủ + bảng giải thích từng field. Xóa câu "Integration will extend...".
2. **§7 demo evidence:** AI đọc `docs/evidence/final-lan-server.log`, `final-lan-pasv-sha256.txt`, `final-lan-active-sha256.txt`, `final-lan-pasv-server.log`. Nhúng trực tiếp vào report:
   - Excerpt server log 18 dòng chứng minh IP, Active sessions, password redacted, reply flow `220→331→230→227→150→226→221`.
   - SHA-256 PASV 3 chiều (source/server/client đều = `b57b64b1...`).
   - SHA-256 ACTIVE 3 chiều (source/server/client đều = `b57b64b1...`).
   - Ghi chú GBN retry PASV và OOO packet ACTIVE recovery.

AI cũng đọc và tổng hợp toàn bộ lịch sử transcript từ 25+ conversation để viết lại `docs/genai-log-b.md` theo format chuẩn với exact prompts và raw output.

**Files changed:** `docs/report.md`, `docs/genai-log-b.md`, `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md`

**Refinement:**
- §5 contribution %, §6 GenAI exact prompts từ A/B, A/C sign-off không thể tự hoàn thiện; cần team quyết định.
- SHA-256 tất cả = `b57b64b198d5d59ce5a22a9b9f25e72a7d081476d432051aa923f3dbebb90934` cho cả PASV lẫn ACTIVE — đây là evidence mạnh nhất về integrity.

---

## Tóm tắt sử dụng GenAI — Role B

| Phiên | Ngày | Kết quả chính |
|---:|---|---|
| 0 | 06/08 | Workflow Role B từ `tuan-2.5-fix.md` |
| 1 | 07/08 | Peer lock, timeout 1s, thêm `transfer_id` vào `RDTHeader` (20 bytes) |
| 2 | 07/08 | Bug audit 15 lỗi; fix B-01/04/05/06/07/08/11; viết lại test thật |
| 3 | 07/08 | Fix B-08/09/12/13; implement START metadata; fill docs |
| 4 | 07/08 | Fix 7 critical bugs (B-S1/S4/R1/R5/R6/S8 + port static); dynamic port tests |
| 5 | 08/08 | 4 black-box tests mới: transfer_id filter, ABORT, FIN grace, length drop; 31 passed |
| 6 | 09/08 | Hướng dẫn verify START ACK/retry; 2 targeted tests; pytest syntax fix |
| 7 | 09/08 | Final RDT verification; 45 passed; bổ sung §2.3/§3.6/§5.2/§7.3 report |
| 8 | 10/08 | §2.2 Session struct đầy đủ; §7 evidence embedded; genai-log-b hoàn thiện |

**Nguyên tắc sử dụng AI của Role B:**
- Mọi code do AI sinh ra đều được đọc hiểu, chạy test và verify trước khi commit.
- Lỗi phát hiện được trong AI output (format string, endianness, `break` vs `continue`) đều được ghi vào mục Refinement.
- AI không thể chạy test tự động → mọi test result đều do team chạy thực tế.
