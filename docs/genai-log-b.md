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
