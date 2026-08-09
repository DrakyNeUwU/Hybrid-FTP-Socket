# 5. Data Channel — UDP/RDT

**Trạng thái:** Hoàn thành  
**Mục tiêu:** Mô tả header, serialization, ACK/retry, FIN/ABORT và bằng chứng kiểm thử cho tầng truyền dữ liệu UDP/RDT.  
**Requirement:** RQ-04, RQ-06, RQ-10, RQ-12. **Owner:** B. **Reviewer:** A/C.  
**Source:** `../../api-contract.md`, `../../requirement-checklist.md`, and
`../../evidence/final-week-rdt-gbn-verification.md`.
**Code:** `common/RDTHeader.py`, `common/rdt_sender.py`, `common/rdt_receiver.py`.

## 5.1 Kiến trúc tầng dữ liệu

Role B đã triển khai một lớp truyền dữ liệu dựa trên UDP với cơ chế tin cậy riêng, tách biệt khỏi kênh điều khiển TCP. Tầng này được thiết kế theo hai thành phần chính:

- `RDTSenderAdapter`: đóng vai trò adapter giữa `TransferManager`/client và logic gửi dữ liệu RDT.
- `RDTReceiverAdapter`: đóng vai trò adapter cho phía nhận, chuyển các chunk dữ liệu đã được kiểm tra và tái lắp thành iterator cho quá trình ghi file.

Các module cốt lõi nằm ở:
- `common/RDTHeader.py`: định nghĩa header 20-byte, flags và checksum.
- `common/rdt_sender.py`: gửi dữ liệu theo mô hình bounded Go-Back-N window, có timeout/retransmission và xử lý FIN/ABORT.
- `common/rdt_receiver.py`: nhận, xác thực checksum/sequence, gửi ACK và kết thúc luồng khi nhận FIN.

## 5.2 Wire format và checksum

Header RDT dùng định dạng big-endian 20 byte với các trường:

- `transfer_id`: định danh transfer.
- `seq_num`: số thứ tự gói dữ liệu.
- `ack_num`: số sequence được xác nhận.
- `flags`: chỉ ra loại gói (`FLAG_DATA`, `FLAG_ACK`, `FLAG_FIN`, `FLAG_START`, `FLAG_ABORT`).
- `checksum`: CRC-32 tính trên header fields và payload.
- `length`: độ dài payload.

Việc kiểm tra checksum được thực hiện ở cả sender và receiver, giúp phát hiện lỗi truyền và ngăn nhận dữ liệu bị hỏng.

## 5.3 Luồng gửi/nhận và recovery

- Sender gửi một `START` packet trước khi bắt đầu window dữ liệu, rồi chờ ACK trước khi đưa thêm packet vào cửa sổ gửi.
- Với mỗi chunk dữ liệu, sender dùng timeout và retry limit để phát hiện mất gói và gửi lại.
- Receiver chỉ chấp nhận packet đúng thứ tự, bỏ qua duplicate/out-of-order và gửi ACK cumulative cho các sequence đã nhận liên tục.
- Khi nhận `FLAG_FIN`, receiver thực hiện grace ACK để xử lý tình huống FIN bị mất hoặc bị lặp lại.
- Khi nhận `FLAG_ABORT`, receiver dừng transfer và báo lỗi rõ ràng, giúp hủy tiến trình truyền nhanh hơn.
- Luồng này phù hợp với kế hoạch tuần 2: Stop-and-Wait là nền tảng, trong khi Go-Back-N window 4 chỉ là bounded enhancement cho việc truyền nhiều packet liên tiếp mà không làm thay đổi header shared contract.

## 5.4 RDT trace flow

The verified RDT flow follows the contract exactly:

- `START` is sent with transfer metadata including the total file size.
- The receiver responds with `ACK` for sequence `0` before data transfer begins.
- The sender streams `DATA` packets in a bounded Go-Back-N window of up to 4 packets.
- The receiver validates checksum and payload length, accepts only the next expected sequence, and returns a cumulative `ACK` for the highest contiguous sequence received.
- On timeout, the sender retransmits the current window and continues until the transfer completes or the retry limit is reached.
- After the final data packet, the sender sends `FIN`.
- The receiver ACKs the `FIN` and remains available to re-ACK duplicate `FIN` packets during a short grace period.
- If cancellation occurs, `ABORT` is used to terminate the transfer immediately and safely.

This trace is recorded as:

- `START → ACK(0)`
- `DATA → ACK(n)` / window advancement
- `FIN → ACK(fin_seq)`
- or `ABORT` on cancellation or fatal error

`START → DATA/ACK → FIN/ACK` is the expected success path, and `ABORT` is the terminal error path.

## 5.5 Bằng chứng kiểm thử

Bộ kiểm thử Role B đã được thực hiện bằng các test riêng cho RDT:

```bash
pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -q
```

Kết quả thực tế:

- `45 passed in 67.09s`

Các trường hợp bao phủ gồm:
- round-trip serialization/deserialization header,
- checksum valid/corrupt,
- packet loss, corruption, ACK loss,
- empty file, chunk-boundary file,
- cancel/abort và retry timeout.

## 5.5 Kết luận kỹ thuật

Tầng UDP/RDT đã được xây dựng thành một phần vận hành thực tế của hệ thống, không chỉ là mô hình giả lập. Các chức năng tin cậy như ACK, retransmission, checksum, FIN/ABORT và fault injection recovery đều đã có bằng chứng kiểm thử thực tế.
