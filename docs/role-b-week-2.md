
# Role B — Week 2 Documentation

> **Shared API:** [`api-contract.md`](api-contract.md)  
> **Requirement checklist:** [`requirement-checklist.md`](requirement-checklist.md)  
> **Trạng thái tài liệu:** `Đã cập nhật — 2026-08-07`

## 1. Phạm vi trách nhiệm

Role B chịu trách nhiệm **UDP data channel / RDT (Reliable Data Transfer)**:

- Thiết kế và triển khai giao thức RDT Stop-and-Wait trên UDP
- `common/RDTHeader.py` — wire format, serialization, checksum
- `common/rdt_sender.py` — `RDTSenderAdapter`, `send_chunks_rdt`, helpers
- `common/rdt_receiver.py` — `RDTReceiverAdapter`, `receive_chunks_rdt`, helpers
- `tests/test_rdt.py` — unit tests và integration tests
- `tests/test_rdt_fault_injection.py` — fault injection tests

**Ranh giới với Role A:** A parse PORT/PASV, tạo `Endpoint` và `TransferContext`, gọi `TransferManager.upload/download`. Role B chỉ nhận socket + context đã validated.  
**Ranh giới với Role C:** C commit file atomic qua `FilesystemService`; B trả iterator chunks, không ghi file trực tiếp trong production path.

## 2. Requirements liên quan đến Role B

| RQ-ID | Nội dung | Trạng thái |
|---|---|---|
| RQ-02 | UDP transport layer với reliability | ✅ Implemented |
| RQ-03 | Stop-and-Wait protocol | ✅ Implemented |
| RQ-04 | Retransmission khi timeout | ✅ Implemented (retry_limit) |
| RQ-05 | ACK mechanism | ✅ Implemented (FLAG_ACK + seq check) |
| RQ-06 | Binary integrity — SHA-256 | ✅ Test evidence trong fault injection |
| RQ-07 | Error recovery — packet loss/corruption | ✅ Test với NetworkProxy |
| RQ-08 | Checksum | ✅ CRC-32 over header fields + payload |
| RQ-09 | FIN/EOF handling | ✅ FLAG_FIN + _fin_grace() |
| RQ-10 | ABORT/cancellation | ✅ FLAG_ABORT + cancel_event |
| RQ-11 | GenAI usage log | ✅ `docs/genai-log-b.md` |

## 3. Thành phần đã triển khai

| Module | Class/Function | Mô tả | Status |
|---|---|---|---|
| `common/RDTHeader.py` | `RDTHeader` | Wire format 20-byte, flags, CRC-32 | ✅ Done |
| `common/rdt_sender.py` | `RDTSenderAdapter` | Protocol adapter cho TransferManager | ✅ Done |
| `common/rdt_sender.py` | `send_chunks_rdt` | Streaming Stop-and-Wait sender | ✅ Done |
| `common/rdt_sender.py` | `send_file_rdt` | Legacy filepath API (backward compat) | ✅ Done |
| `common/rdt_sender.py` | `_lookahead` | Detect FIN không cần `list()` | ✅ Done |
| `common/rdt_sender.py` | `_send_abort` | Gửi ABORT best-effort | ✅ Done |
| `common/rdt_sender.py` | `_send_start` | Gửi START packet (file size) | ✅ Done |
| `common/rdt_receiver.py` | `RDTReceiverAdapter` | Protocol adapter cho TransferManager | ✅ Done |
| `common/rdt_receiver.py` | `receive_chunks_rdt` | Streaming generator receiver | ✅ Done |
| `common/rdt_receiver.py` | `receive_file_rdt` | Legacy filepath API (backward compat) | ✅ Done |
| `common/rdt_receiver.py` | `_send_ack` | Gửi ACK | ✅ Done |
| `common/rdt_receiver.py` | `_fin_grace` | Re-ACK duplicate FIN grace period | ✅ Done |
| `tests/test_rdt.py` | `TestRDTHeader` | Unit tests header serialization/checksum | ✅ Done |
| `tests/test_rdt.py` | `TestRDTSendReceiveIntegration` | Integration test localhost UDP | ✅ Done |
| `tests/test_rdt.py` | `TestRDTProtocolLogic` | Protocol logic tests | ✅ Done |
| `tests/test_rdt_fault_injection.py` | `NetworkProxy` | Drop/corrupt proxy | ✅ Done |
| `tests/test_rdt_fault_injection.py` | `TestRDTFaultInjection` | SHA-256 integrity, loss, corrupt | ✅ Done |

## 4. Thành phần chưa triển khai

| Item | Lý do | Priority |
|---|---|---|
| START ACK handshake | START hiện là best-effort; nếu mất, receiver không biết file size | P2 |
| transfer_id UUID 16-byte | Contract §7 đề xuất 16 bytes; hiện dùng 4-byte int (team decision needed) | P2 |
| Sliding window / Go-Back-N | Stop-and-Wait đủ cho demo; performance improvement | P3 |

## 5. Blocker hiện tại

- **Python chưa được cài trên máy** → không chạy được pytest để lấy test output thực tế
- **transfer_id format** — team chưa quyết định UUID vs int; ảnh hưởng wire format và backward compat

## 6. Công việc ưu tiên

1. [P1] Cài Python và chạy `pytest tests/test_rdt.py tests/test_rdt_fault_injection.py -v` để lấy evidence
2. [P1] Wire `RDTSenderAdapter`/`RDTReceiverAdapter` vào `TransferManager` production path
3. [P2] Team quyết định transfer_id format (B-03)
4. [P3] Thêm START ACK handshake nếu cần

## 7. Module/file phụ trách

```
common/RDTHeader.py          — wire format, flags, checksum
common/rdt_sender.py         — sender (adapter + core + helpers)
common/rdt_receiver.py       — receiver (adapter + core + helpers)
tests/test_rdt.py            — unit + integration tests
tests/test_rdt_fault_injection.py — fault injection + SHA-256 evidence
```

## 8. Shared API đang sử dụng

Theo `api-contract.md §3` và `§4`:

```python
# Role B implements:
class RDTSenderAdapter:
    def send(self, chunks, data_socket, endpoint, context) -> int: ...

class RDTReceiverAdapter:
    def receive(self, data_socket, endpoint, context) -> Iterable[bytes]: ...
```

`TransferContext` fields được truy cập qua `getattr` với fallback để tương thích với test doubles.

## 9. RDT header và serialization

**Wire layout — big-endian, 20 bytes:**

| Field | Offset | Size | Type | Meaning |
|---|---|---|---|---|
| `transfer_id` | 0 | 4 | `I` (uint32) | Per-transfer opaque ID |
| `seq_num` | 4 | 4 | `I` | DATA/FIN sequence number |
| `ack_num` | 8 | 4 | `I` | Acknowledged sequence |
| `flags` | 12 | 2 | `H` | Bitmask FLAG_* |
| `checksum` | 14 | 4 | `I` | CRC-32 (header fields + payload) |
| `length` | 18 | 2 | `H` | Payload bytes |

**Flags (không xung đột):**

| Flag | Value | Meaning |
|---|---|---|
| `FLAG_DATA` | `0x01` | Data packet |
| `FLAG_ACK` | `0x02` | Acknowledgement |
| `FLAG_FIN` | `0x04` | Final packet (EOF) |
| `FLAG_START` | `0x08` | Transfer start (file size metadata) |
| `FLAG_ABORT` | `0x10` | Cancel/abort |

Format string: `"!IIIHIH"` → `struct.calcsize` = 20 bytes.  
**Checksum:** CRC-32 (`zlib.crc32`) over header fields (transfer_id, seq_num, ack_num, flags, length) + payload. Checksum field tự nó không được include.

## 10. Sender/receiver state machine

**Sender:**
```
INIT
  → send START (best-effort, no ACK)
  → for each chunk:
      SEND_DATA[seq]
        → timeout → RETRANSMIT (up to retry_limit)
        → ACK received (flags & FLAG_ACK, ack_num == seq) → NEXT_CHUNK
        → cancel_event → SEND_ABORT → RAISE
        → retry_limit exceeded → RAISE RuntimeError
  → last chunk: set FLAG_FIN
  → DONE (socket.close() in finally)
```

**Receiver:**
```
WAIT_PACKET
  → START packet → extract total_bytes → continue
  → ABORT → raise RuntimeError
  → Checksum fail → drop
  → seq == expected → yield payload, send ACK
      → FLAG_FIN → _fin_grace (re-ACK duplicate FIN) → DONE
  → seq < expected → re-ACK, drop (duplicate)
  → seq > expected → drop (out-of-order)
  → timeout × max_timeouts → raise RuntimeError
```

## 11. Stop-and-Wait, ACK, sequence và checksum

- **Stop-and-Wait:** sender gửi 1 packet, chờ ACK trước khi gửi tiếp
- **Sequence:** 0-indexed `seq_num`, tăng dần; ACK mang `ack_num == seq` của packet được ACK
- **Peer locking:** sau gói đầu tiên, receiver chỉ chấp nhận từ đúng `(ip, port)` đó
- **transfer_id locking:** chỉ accept packet có đúng transfer_id
- **Checksum:** CRC-32 bao gồm cả header fields → không thể forge header mà không bị phát hiện
- **Edge cases tested:** empty file, exact chunk boundary, DATA+FIN combination

## 12. Timeout, retransmission và retry limit

| Constant | Sender | Receiver |
|---|---|---|
| Default timeout | `0.5s` | `1.0s` |
| Default retry limit | `10` retries | `10 × 1s = 10s inactivity` |
| Overridable via | `TransferContext.timeout_seconds/retry_limit` | `TransferContext.timeout_seconds` |

Sau khi vượt retry_limit: sender raise `RuntimeError`, socket đóng trong `finally`.

## 13. Duplicate, out-of-order và payload-length validation

- **Duplicate** (`seq < expected_seq`): re-ACK, không yield (tránh ghi 2 lần)
- **Out-of-order** (`seq > expected_seq`): drop, không ACK (tránh hỏng sequence)
- **Payload-length**: `payload = data[header.size : header.size + header.length]`; checksum verify trên đúng payload này
- **Min packet size**: bỏ qua nếu `len(data) < RDTHeader.size`

## 14. Transfer ID, FIN/EOF và ABORT/cancellation

- **Transfer ID:** random `uint32` trong legacy API; từ `TransferContext.transfer_id` trong adapter (hash SHA-256 nếu là str UUID)
- **FIN:** chunk cuối set `FLAG_FIN`; receiver sau khi ACK FIN chạy `_fin_grace()` (3 lần, re-ACK nếu sender retransmit FIN)
- **ABORT:** sender gửi ABORT best-effort khi `cancel_event` set; receiver raise `RuntimeError("Transfer aborted by sender")`
- **Socket cleanup:** `send_chunks_rdt` dùng `finally: udp_socket.close()`; legacy receiver socket do caller quản lý

## 15. Active/PASV integration và progress callback

**Progress callback contract** (api-contract.md §8):
```python
progress_cb(transfer_id: str, acknowledged_bytes: int, total_bytes: int | None) -> None
```

- Sender: gọi sau mỗi ACK thành công với `transferred_bytes` và `total_bytes` (từ `os.path.getsize`)
- Receiver: gọi sau mỗi chunk được commit với `committed_bytes` và `total_bytes` (từ START packet)
- Legacy API wrap `progress_cb(acked, total)` → adapter contract

## 16. Cleanup và thread-safety

- Sender socket: tạo và đóng trong `send_chunks_rdt` — không shared với thread khác
- Receiver socket: tạo bởi caller (test/TransferManager); legacy `receive_file_rdt` không đóng socket (caller chịu trách nhiệm)
- `cancel_event`: `threading.Event` shared an toàn; checked ở đầu mỗi vòng lặp
- Cleanup file khi fail: `receive_file_rdt` xóa partial file trong `except RuntimeError`

## 17. Test bắt buộc

| Test | File | Loại |
|---|---|---|
| Header serialize/deserialize roundtrip | `test_rdt.py::TestRDTHeader::test_serialize_deserialize_roundtrip` | Unit |
| Checksum valid/corrupt/payload-corrupt | `test_rdt.py::TestRDTHeader::test_checksum_*` | Unit |
| FLAG_DATA ≠ 0, flag bitmask combinations | `test_rdt.py::TestRDTHeader::test_flag_*` | Unit |
| Checksum covers header fields | `test_rdt.py::TestRDTHeader::test_checksum_different_seq_*` | Unit |
| Integration transfer small/empty/multi-chunk | `test_rdt.py::TestRDTSendReceiveIntegration::test_*` | Integration |
| Stop-and-Wait logic | `test_rdt.py::TestRDTProtocolLogic::test_*` | Unit |
| Transfer sạch SHA-256 match | `test_rdt_fault_injection.py::test_clean_transfer_sha256` | Fault injection |
| Drop 15% recovery | `test_rdt_fault_injection.py::test_packet_loss_recovery` | Fault injection |
| Corrupt 10% recovery | `test_rdt_fault_injection.py::test_corruption_recovery` | Fault injection |
| Drop+corrupt combined | `test_rdt_fault_injection.py::test_loss_and_corruption_recovery` | Fault injection |
| Empty file transfer | `test_rdt_fault_injection.py::test_empty_file_transfer` | Edge case |
| Chunk boundary file | `test_rdt_fault_injection.py::test_chunk_boundary_file` | Edge case |
| Cancel stops sender fast | `test_rdt_fault_injection.py::test_cancel_stops_transfer` | Cancel |

## 18. Evidence cần bàn giao

```bash
# Chạy unit tests
pytest tests/test_rdt.py -v

# Chạy fault injection tests (cần ~30s với drop+corrupt)
pytest tests/test_rdt_fault_injection.py -v

# SHA-256 evidence: test_clean_transfer_sha256 log file hash match
```

**Reviewer:** team A (xác nhận adapter contract), team C (xác nhận FilesystemService integration).

## 19. Rủi ro kỹ thuật và dependency với role khác

| Rủi ro | Dependency | Mitigation |
|---|---|---|
| transfer_id format change (B-03) | A tạo transfer_id, B serialize vào header | Dùng hash fallback; chờ team decision |
| Adapter không được wire vào production | A/C cần inject `RDTSenderAdapter`/`RDTReceiverAdapter` vào `TransferManager` | Documented trong `rdt_sender.py` docstring |
| START packet bị mất → progress không có % | Best-effort design | Acceptable; progress vẫn báo bytes tuyệt đối |
| Port conflicts trong tests | Các test dùng ports 19900–19912 | Fixed ports; cần isolate nếu chạy song song |

## 20. Definition of Done của Role B

- [x] Role B xác nhận header/API khớp [`api-contract.md`](api-contract.md) §3, §4, §7
- [x] Sender/receiver production path có test reliability và cleanup
- [x] FIN và ABORT có implementation và test coverage
- [x] SHA-256 binary evidence có trong `test_rdt_fault_injection.py`
- [ ] Active/PASV adapter wired trong production (chờ A integration)
- [ ] Test chạy thành công trên CI/máy đã cài Python

## 21. Self-assessment dựa trên bằng chứng

**Đã hoàn thành:**
- RDT header format chuẩn, checksum cover header + payload
- Stop-and-Wait sender/receiver với streaming (không `list()` vào RAM)
- Protocol adapter class (`RDTSenderAdapter`, `RDTReceiverAdapter`) implement api-contract §3
- Tests thật (không phải boolean simulation) — integration test trên localhost UDP
- Fault injection tests với NetworkProxy, SHA-256 verification
- ABORT, FIN grace, cancel_event, resource cleanup

**Chưa có evidence thực tế:** chưa chạy được pytest do Python chưa cài.

## 22. Checklist requirement tương ứng

| RQ-ID | Trạng thái | Evidence |
|---|---|---|
| RQ-02 (UDP transport) | ✅ Done | `rdt_sender.py`, `rdt_receiver.py` |
| RQ-03 (Stop-and-Wait) | ✅ Done | `send_chunks_rdt` loop |
| RQ-04 (Retransmission) | ✅ Done | `retry_limit` loop |
| RQ-05 (ACK) | ✅ Done | `FLAG_ACK`, `ack_num` check |
| RQ-06 (SHA-256 integrity) | ✅ Done | `test_clean_transfer_sha256` |
| RQ-07 (Error recovery) | ✅ Done | `test_packet_loss_recovery`, `test_corruption_recovery` |
| RQ-08 (Checksum) | ✅ Done | CRC-32 in `RDTHeader.compute_checksum` |
| RQ-09 (FIN/EOF) | ✅ Done | `FLAG_FIN`, `_fin_grace` |
| RQ-10 (ABORT) | ✅ Done | `FLAG_ABORT`, `_send_abort` |
| RQ-11 (GenAI log) | ✅ Done | `docs/genai-log-b.md` |
