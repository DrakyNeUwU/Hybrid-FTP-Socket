# GenAI Usage Log — Role B

Format mỗi lần dùng AI:

**Prompt:** [mô tả yêu cầu]  
**Raw output:** [tóm tắt output thô]  
**Refinement:** (mình đã sửa/hiểu gì, lỗi/hạn chế phát hiện được)

---

## 2026-08-07 — Bug Audit và Fix (Phiên 1)

**Prompt:**
> "fix cac loi uu tien roi doc cac file lien quan toi role B, tổng hợp lại các lỗi còn mắc phải"

**Raw output:**
AI đọc `RDTHeader.py`, `rdt_sender.py`, `rdt_receiver.py`, `test_rdt.py`, `test_rdt_fault_injection.py` và `api-contract.md`. Phát hiện 15 lỗi (B-01 đến B-15), phân loại theo độ ưu tiên. Đề xuất fix cho các lỗi ưu tiên cao trước.

**Fixes thực hiện (AI-assisted):**

| # | Fix | Tự kiểm tra |
|---|---|---|
| B-01 | Tạo `RDTSenderAdapter` / `RDTReceiverAdapter` class implement api-contract §3 Protocol | Đọc api-contract.md, kiểm tra signature |
| B-02 | Adapter dùng `getattr(context, field, default)` để đọc TransferContext fields | Review TransferContext dataclass |
| B-04 | `receive_file_rdt` không đóng socket — comment rõ ràng caller chịu trách nhiệm | Review test code |
| B-05 | `receive_file_rdt` streaming (không `list()` vào RAM) — dùng generator trực tiếp | Code review |
| B-06 | `send_chunks_rdt` lookahead-1 iterator (`_lookahead`) — detect FIN mà không `list()` | Unit test trong `test_rdt.py` |
| B-07 | Thay boolean simulation bằng integration test thật trên localhost UDP | Manual review test logic |
| B-08 | `recvfrom(65535)` → `recvfrom(_RECV_BUF = RDTHeader.size + 1024 + 64)` | Kiểm tra header.size và chunk size |
| B-09 | Thêm `_send_start()` gửi file size; receiver extract từ START packet | Review FLAG_START |
| B-11 | `NetworkProxy` dùng `dict` thay `last_client_addr` — tránh race condition | Review threading |

**Refinement (lỗi/hạn chế phát hiện):**
- AI tạo `compute_checksum` với format string `"!IIIH H"` (có space thừa) → bị lỗi `struct.error`. Đã tự sửa thành `"!IIIHI"`.
- AI không thể chạy pytest (Python chưa cài) → không có test output thực tế. Cần chạy tay để xác nhận.
- B-03 (transfer_id UUID 16-byte) và B-12/B-13 (documentation) được AI ghi nhận là lỗi nhưng cần team decision cho B-03.

---

## 2026-08-07 — Bug Audit và Fix (Phiên 2)

**Prompt:**
> "tiếp tục fix" (từ conversation mới)

**Raw output:**
AI đọc transcript phiên trước, xác định B-08, B-09, B-12, B-13 còn thiếu. Thực hiện:
- B-08: Fix `recvfrom` buffer từ `65535` → `_RECV_BUF = 1108 bytes`
- B-09: Thêm START packet với file size metadata
- B-12: Điền toàn bộ `role-b-week-2.md`
- B-13: Điền `genai-log-b.md` (file này)

**Refinement:**
- START packet là best-effort (không có ACK handshake) — nếu mất thì receiver không biết total_bytes, nhưng vẫn nhận data bình thường. Acceptable cho demo.
- `_RECV_BUF` cố định tại 1108; nên parameterize theo `chunk_size` từ TransferContext trong future.
- AI không tự chạy test được → evidence phải do team tự chạy.

---

## 2026-08-07 — Bug Audit và Fix (Phiên 3)

**Prompt:**
> "đọc file tuan-2.5-fix.md rồi đọc các file liên quan tới role B, đưa ra các lỗi"
> "sửa các file bị lỗi"
> "đưa câu lệnh để tôi compile các file này"

**Raw output:**
AI phân tích `tuan-2.5-fix.md` và các file của Role B. Phát hiện các lỗi nghiêm trọng về việc Sender bỏ qua data_socket truyền từ TransferManager, checksum/length của ACK không được validate đầy đủ, tổ hợp flag không hợp lệ, lỗi `break` làm ngắt sớm vòng lặp `_fin_grace` của Receiver, và test sử dụng cổng tĩnh dễ xung đột. AI đã đề xuất sửa đổi và chỉnh sửa đồng loạt các file:
- `common/RDTHeader.py`: Thêm validate flag (`is_valid_flags`) và validate độ dài (`validate_length`).
- `common/rdt_sender.py`: Sửa đổi để sử dụng external `data_socket` do TransferManager cấp; validate checksum/length của ACK nhận về; dùng resolved IP cho ABORT packet; và chuẩn hóa định dạng payload của START packet (big-endian).
- `common/rdt_receiver.py`: Fix hằng số `max_timeouts`; validate length của gói nhận được; validate checksum của START packet; khóa peer (peer lock) sau gói đầu tiên hợp lệ; sửa lỗi dùng `break` thành `continue` trong `_fin_grace` để không thoát sớm.
- `tests/test_rdt.py` & `tests/test_rdt_fault_injection.py`: Thay đổi các mock test cũ thành test thật chạy qua production code; chuyển đổi cổng static sang dynamic để tránh xung đột cổng.

**Refinement:**
- Việc chuyển sang dynamic ports giúp test không bị flaky hoặc conflict khi chạy song song.
- Chuyển từ mock logic sang gọi production adapter giúp tăng độ tin cậy và phản ánh đúng thực tế truyền nhận RDT.
- Tuy nhiên, AI chưa thể chạy trực tiếp pytest do thiếu môi trường, việc chạy test vẫn phải do team thực thi thủ công hoặc cấu hình CI.

---

## 2026-08-09 — Black-box Testing (Phiên 4)

**Prompt:**
> "đọc file test_rdt.py để xây dựng black-box testing tiếp theo"
> "dựa vào file test_rdt.py, xây dựng black-box testing phù hợp"
> "thêm phần black-box testing vào file test_rdt.py"

**Raw output:**
AI đã đọc và phân tích cấu trúc của file `tests/test_rdt.py`. Dựa trên kết quả phân tích, AI đề xuất và lập trình 4 kịch bản kiểm thử hộp đen mới để củng cố tính đúng đắn cho giao thức RDT (Task B-F01):
- `test_receiver_ignores_different_transfer_id`: Kiểm tra bỏ qua gói tin có transfer ID sai.
- `test_receiver_aborts_on_abort_packet`: Kiểm tra xử lý dừng kết nối khi nhận cờ ABORT.
- `test_receiver_graceful_fin_ack_retransmission`: Kiểm tra phản hồi ACK cho gói FIN trùng lặp trong grace period.
- `test_receiver_drops_invalid_length_packet`: Kiểm tra loại bỏ gói tin có độ dài payload thực tế không khớp với trường length trong header.

**Refinement:**
- Đảm bảo các test case mới được thêm trực tiếp vào file `tests/test_rdt.py` mà không thay đổi bất kỳ dòng code cũ nào của hệ thống.
- Chạy bộ test suite thành công (31/31 tests pass) trên môi trường cục bộ để xác minh tính ổn định.

---

## 2026-08-09 — Hướng dẫn kiểm tra gói START (Phiên 5)

**Prompt:**
> "hướng dẫn thực hiện Kiểm tra xem gói START có được ACK và retry hữu hạn theo thiết kế của C-F01 hay không"

**Raw output:**
AI đã phân tích mã nguồn và cung cấp hướng dẫn kiểm tra thiết kế tin cậy của gói START:
- **Tĩnh**: Chỉ ra hàm `_send_start_with_ack` trong `common/rdt_sender.py` có vòng lặp giới hạn bởi `retry_limit` để thực hiện truyền lại gói START (với cờ `FLAG_START`, `seq_num=0`) khi gặp `socket.timeout`. Nếu nhận đúng ACK (`ack_num=0`), nó kết thúc thành công; nếu hết lượt thử mà không có ACK, nó ném `RuntimeError`. Phía nhận `common/rdt_receiver.py` xử lý cờ START và gửi lại ACK (`ack_num=0`) mỗi khi nhận được.
- **Động (Chạy test)**: Chỉ ra 2 hàm kiểm thử tự động trong `tests/test_rdt.py` thuộc lớp `TestRDTProtocolLogic` để xác minh thiết kế:
  - `test_start_ack_loss_retries_before_data_window` (mất ACK đầu của START).
  - `test_max_retry_limit_raises_runtime_error` (mất hết ACK và đạt giới hạn thử lại).
- **Lệnh chạy**:
  `py -m pytest tests/test_rdt.py::TestRDTProtocolLogic::test_start_ack_loss_retries_before_data_window tests/test_rdt.py::TestRDTProtocolLogic::test_max_retry_limit_raises_runtime_error`

**Refinement:**
- Đã xác thực lệnh chạy trực tiếp các test cases thành công và không bị deselected các bài test khác.

---

## 2026-08-09 — Final RDT verification (Phiên 6)

**Prompt:**
> "kiểm tra lại toàn bộ role B sau khi đã sửa và ghi lại evidence cho report"

**Raw output:**
AI đã đối chiếu lại implementation với planning và tài liệu Role B week 2, sau đó đề xuất cập nhật các draft báo cáo cho phần UDP/RDT. Mã nguồn được kiểm tra qua các module `common/RDTHeader.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`, cùng bộ test `tests/test_rdt.py` và `tests/test_rdt_fault_injection.py`.

**Verification thực tế:**
- Chạy lệnh: `python3 -m pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q`
- Kết quả: **45 passed in 67.09s**

**Refinement:**
- Đây là bằng chứng chính để ghi vào các file report-parts cho Role B: technical draft, testing results, requirement compliance và contribution matrix.
- Việc dùng `python3 -m pytest` thay vì `pytest` giúp tránh nhầm môi trường Python và phù hợp với môi trường WSL2 hiện tại.
- Những phần liên quan đến B-F02/B-F03 cần ghi rõ là đã có evidence thực tế, không còn là placeholder.

## 2026-08-09 — Final Role B completion

**Summary:**
- Role B finalized the RDT contract review and documentation updates for the final report.
- `docs/report-parts/technical/05-data-channel-rdt.md` now explicitly documents the START → DATA/ACK → FIN/ACK trace and ABORT behavior.
- `docs/api-contract.md` was updated to reflect the final contract review status.
- `docs/report.md` was extended with requirement traceability and the final evidence summary.
- `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md` now includes the Role B final checklist and task status.

**Outcome:**
- The final report, contract summary, and evidence capture are aligned with the implemented wire protocol.
- The RDT documentation is now consistent with the 20-byte header, FLAG_START handshake, Go-Back-N window 4 behavior, FIN/ACK termination, and ABORT cancellation paths.
- The final test evidence is recorded as `45 passed in 67.09s` for the RDT-focused suites and `199 passed in 96.72s` for the full regression.

