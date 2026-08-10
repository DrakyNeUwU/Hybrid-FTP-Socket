# B-F03: Oral Pack — RDT Protocol & System Integration

**Owner:** Role B  
**Date:** 2026-08-10  
**Purpose:** 20 core oral questions + file locators + live coding locators for RDT, protocol contract, and system understanding.

---

## Part 1: RDT Protocol Core (Ownership B)

### Q1: RDT Header Structure
**Question:** Mô tả cấu trúc header RDT 20 byte. Mỗi field là gì, kích thước bao nhiêu, và có checksum như thế nào?

**Answer:** 
- `magic` (2 bytes): 0xABCD (identify valid packet)
- `command` (1 byte): 0x01=DATA, 0x02=ACK, 0x03=FIN, 0x04=ABORT, 0x05=START
- `flags` (1 byte): Sequencing, ACK tích lũy
- `transfer_id` (4 bytes): Unique transfer session ID
- `sequence` (4 bytes): Packet sequence number
- `ack_sequence` (4 bytes): Expected next sequence (cumulative ACK)
- `data_length` (2 bytes): Payload length (0–1024 bytes)
- `checksum` (2 bytes): CRC16 of header + payload

**File locator:** [common/RDTHeader.py](common/RDTHeader.py#L1-L50)

---

### Q2: START Metadata Reliability
**Question:** Làm sao START packet được xác nhận? Nếu receiver không nhận được START, điều gì sẽ xảy ra?

**Answer:**
- START packet là DATA command `0x01` mang metadata (filename, size, mode).
- Receiver gửi ACK ngay khi nhận START; ACK có `ack_sequence` chỉ đến byte tiếp theo.
- Sender timeout (thường 1s) không nhận ACK → retransmit START (tối đa 3 lần).
- Nếu fail hết retry → Sender trả error (425 Can't Open Data Connection) qua TCP.
- Receiver cleanup: xóa `.part` file nếu START không thành công hoặc mất ACK từ sender.

**File locator:** 
- [common/rdt_sender.py](common/rdt_sender.py#L80-L130) - START send + retry
- [common/rdt_receiver.py](common/rdt_receiver.py#L60-L110) - START receive + ACK
- [tests/test_rdt.py](tests/test_rdt.py#L200-L250) - START retry test

---

### Q3: Go-Back-N Window Management
**Question:** Explain Go-Back-N window size 4. Khi nào timeout xảy ra, từ packet nào retransmit?

**Answer:**
- Window size = 4 packets: tối đa 4 packets có thể gửi mà không chờ ACK.
- ACK tích lũy (cumulative): ACK#5 có nghĩa "tôi đã nhận được bytes 0–4, mong đợi #5".
- Timeout: nếu không nhận ACK cho packet đầu tiên trong window → retransmit từ packet đó (không phải cả window).
- Sliding window: khi nhận ACK#N → xóa packets 0 to N-1 khỏi send buffer; thêm packet mới vào cuối (nếu còn dữ liệu).
- Flow control: sender không bao giờ keep >4 unACKed packets in-flight → tránh flood UDP.

**File locator:**
- [common/rdt_sender.py](common/rdt_sender.py#L140-L200) - Window management + retransmit logic
- [tests/test_rdt_fault_injection.py](tests/test_rdt_fault_injection.py#L100-L150) - Window exhaustion test

---

### Q4: Duplicate Detection & Out-of-Order Handling
**Question:** Nếu receiver nhận 2 packets giống nhau (duplicate) hoặc packets bị disorder, điều gì xảy ra?

**Answer:**
- Duplicate: Receiver track `expected_sequence`. Nếu nhận packet có seq < expected → discard + vẫn ACK cái seq expected (không re-ACK).
- Out-of-order: packet bị disorder → receiver buffer nó, gửi ACK chỉ tới seq liên tục nhận được (cumulative). Sender thấy ACK cũ → hiểu có packet chưa tới → timeout + retransmit.
- Hash không bị lặp lại vì receiver chỉ add unordered bytes vào file nếu nó là next expected piece (sequential write).

**File locator:**
- [common/rdt_receiver.py](common/rdt_receiver.py#L130-L180) - Duplicate/disorder detection
- [tests/test_rdt_fault_injection.py](tests/test_rdt_fault_injection.py#L160-L200) - Duplicate + disorder test

---

### Q5: Checksum & Corruption Detection
**Question:** Checksum được tính thế nào? Nếu payload bị corrupt, điều gì xảy ra?

**Answer:**
- Checksum là CRC16 trên toàn bộ header (18 bytes) + payload (0–1024 bytes).
- Receiver tính lại CRC16 → so sánh với field checksum. Nếu khác → packet bị discard (không ACK).
- Sender timeout không nhận ACK → retransmit.
- Không bao giờ accept corrupt data vào file; FIN chỉ được ghi sau khi toàn bộ dữ liệu được verify.

**File locator:**
- [common/rdt_utils.py](common/rdt_utils.py#L1-L30) - CRC16 implementation
- [common/RDTHeader.py](common/RDTHeader.py#L60-L100) - Checksum calculation
- [tests/test_rdt_fault_injection.py](tests/test_rdt_fault_injection.py#L50-L100) - Corruption injection test

---

### Q6: FIN Packet & Graceful Closure
**Question:** File transfer xong → FIN packet được gửi như thế nào? Receiver cần làm gì?

**Answer:**
- Sender gửi data tới hết → send FIN packet (command 0x03) với dữ liệu cuối (nếu còn) hoặc rỗng.
- FIN có sequence number tiếp theo expected bytes; receiver biết file complete.
- Receiver ACK FIN; nếu không ACK → sender retry FIN (timeout).
- Receiver finalize file: đổi tên từ `filename.part` → `filename`; close file handle.
- Sender: sau khi nhận ACK(FIN) → close transfer context.

**File locator:**
- [common/rdt_sender.py](common/rdt_sender.py#L240-L280) - FIN send + finalize
- [common/rdt_receiver.py](common/rdt_receiver.py#L200-L250) - FIN receive + rename
- [tests/test_rdt.py](tests/test_rdt.py#L300-L350) - FIN graceful closure test

---

### Q7: ABORT Packet & Error Recovery
**Question:** Khi ABOR command được gửi từ client (qua TCP), sender/receiver phải làm gì?

**Answer:**
- ABOR command: client gửi `ABOR\r\n` qua TCP control channel → server's `CommandHandler` xử lý.
- `TransferManager` nhận lệnh → gửi ABORT packet (command 0x04) qua UDP cho receiver.
- Receiver nhận ABORT → dừng receive; xóa `.part` file; close context.
- Sender dừng retransmit; xóa unACKed packets; close context.
- TCP reply: server gửi `226 Closing data connection` (thành công) hoặc `425 Can't Open Data Connection` (lỗi).

**File locator:**
- [server/transfer_manager.py](server/transfer_manager.py#L150-L200) - ABOR handling
- [common/rdt_sender.py](common/rdt_sender.py#L300-L320) - ABORT receive + cleanup
- [common/rdt_receiver.py](common/rdt_receiver.py#L260-L290) - ABORT receive + cleanup
- [tests/test_rdt.py](tests/test_rdt.py#L400-L450) - ABORT + cleanup verification

---

### Q8: Timeout & Retry Policy
**Question:** Timeout được set bao lâu? Retry tối đa mấy lần? Khi nào fail để trả lỗi?

**Answer:**
- Timeout: 1 second (can adjust nếu network slow); `socket.settimeout(1)`.
- Retry: tối đa 3 lần cho START; 2 lần cho DATA/FIN (default; tunable).
- Retry exhausted: START → trả 425; DATA → trả 426; FIN → trả 426.
- Backoff strategy: có thể exponential hoặc fixed; hiện tại fixed 1s.
- Nếu lỗi → `TransferManager` cleanup: xóa `.part`, close transfer context, trả TCP error.

**File locator:**
- [common/rdt_context.py](common/rdt_context.py#L30-L60) - Timeout config
- [common/rdt_sender.py](common/rdt_sender.py#L30-L80) - Retry loop + timeout handling
- [common/rdt_receiver.py](common/rdt_receiver.py#L20-L40) - Timeout config

---

## Part 2: Integration & System Flow (B understanding; A/C ownership)

### Q9: TCP Control + UDP Data Separation
**Question:** Làm sao TCP control channel và UDP data channel tách biệt nhưng vẫn đồng bộ?

**Answer:**
- TCP (client-server): tất cả FTP command/reply đi qua TCP (port 21 server-side).
- UDP (client-server): file data đi qua UDP (port ephemeral server-side; client phải biết từ PASV/PORT reply).
- Đồng bộ: Session object giữ `transfer_mode` và `transfer_id` trên TCP; TransferManager track transfer trên UDP bằng transfer_id.
- Mode flow: Client gửi MODE S → Session update; Transfer lúc sau dùng mode S khi STOR/RETR.
- Data transfer → TCP trả 150; transfer xong → TCP trả 226. Nếu RDT lỗi → TCP trả 4xx.

**File locator:**
- [server/session.py](server/session.py#L1-L50) - Session + transfer_id management
- [server/transfer_manager.py](server/transfer_manager.py#L1-L100) - Transfer context + mode binding
- [docs/api-contract.md](docs/api-contract.md) - TCP/UDP port + data flow contract

---

### Q10: MODE S (Stream) Data Path
**Question:** MODE S (Stream) có nghĩa gì? Dữ liệu được gửi thế nào so với MODE B/C?

**Answer:**
- MODE S: Stream mode (mặc định). Dữ liệu được gửi dạng continuous byte stream; không có record boundary.
- Sender: gửi data packets sequentially; FIN chỉ mark end.
- Receiver: ghi bytes liên tục vào file; no marker → rely on FIN để biết hết.
- So sánh: MODE B (Block) + MODE C (Compressed) chưa implement; trả 502 nếu client yêu cầu.
- SHA-256: dùng bytes vào file; MODE S không có overhead.

**File locator:**
- [server/command_handler.py](server/command_handler.py#L220-L240) - MODE S handling
- [docs/api-contract.md](docs/api-contract.md) - MODE S specification
- [tests/test_commands.py](tests/test_commands.py#L150-L200) - MODE S command test

---

### Q11: Active vs. PASV Data Connection
**Question:** Active Mode vs. PASV Mode khác nhau thế nào? Client liên hệ server như thế nào?

**Answer:**
- **PASV (Passive)**: Server listen trên port ephemeral (ví dụ 6000); reply `227 Entering Passive Mode (127,0,0,1,23,112)` → client tính port = 23*256+112 = 6000; client connect tới server:6000.
- **Active (PORT)**: Client tell server: `PORT 127,0,0,1,24,112` → server connect lại client:6144 để gửi/nhận data.
- Transfer: sau khi PASV/PORT, client gửi STOR/RETR → server accept/connect data connection → transfer RDT payload qua UDP.
- Firewall: PASV dễ dùng từ behind firewall (outbound); Active yêu cầu firewall mở inbound.

**File locator:**
- [server/command_handler.py](server/command_handler.py#L150-L200) - PASV/PORT command handling
- [server/transfer_manager.py](server/transfer_manager.py#L50-L100) - Data connection setup (listen/connect)
- [docs/api-contract.md](docs/api-contract.md#L100-L150) - PASV/PORT reply format

---

### Q12: Session Isolation & Multi-client
**Question:** Làm sao server xử lý 3 clients đồng thời mà không bị cross-contamination?

**Answer:**
- Mỗi client connection → mới Session object (unique socket).
- Session.transfer_id → unique UUID cho transfer; TransferManager track bằng transfer_id.
- Lock (threading.Lock): transfer_id lock để tránh race condition; mỗi session có riêng.
- Filesystem: atomic upload (`filename.part` lock; STOU/APPE không conflict).
- TCP reply chỉ gửi tới client connection tương ứng.
- Nếu client A ABOR → chỉ xóa transfer_A; client B C vẫn chạy độc lập.

**File locator:**
- [server/session.py](server/session.py#L50-L150) - Session class + isolation
- [server/transfer_manager.py](server/transfer_manager.py#L180-L250) - Transfer context + lock
- [server/threaded_server.py](server/threaded_server.py#L1-L100) - Thread per client
- [tests/test_transfer_manager.py](tests/test_transfer_manager.py) - Concurrency tests

---

## Part 3: Live Coding & Code Locators (B responsibility)

### Q13: Find START Retry Logic
**Question:** Tìm code thực hiện START retry. Nếu muốn change timeout từ 1s → 2s, sửa ở đâu?

**Answer & Locator:**
- **File:** [common/rdt_sender.py](common/rdt_sender.py#L80-L130)
- **Code pattern:** `for attempt in range(MAX_START_RETRIES):` → loop retry.
- **Timeout line:** `self.sock.settimeout(self.timeout)` (line ~95)
- **Change:** Update `self.timeout = 2` hoặc `MAX_START_RETRIES` constant.
- **Verify:** Run test [tests/test_rdt.py#L200-L250](tests/test_rdt.py#L200-L250) để check retry hoạt động.

---

### Q14: Find ACK Cumulative Logic
**Question:** Tìm code handle cumulative ACK. Làm sao biết packets nào cần retransmit?

**Answer & Locator:**
- **File:** [common/rdt_sender.py](common/rdt_sender.py#L140-L200)
- **Code pattern:** `ack_seq = unpack_ack(ack_packet)` → extract ACK sequence.
- **Sliding window:** `self.send_buffer = self.send_buffer[ack_seq:]` → discard ACKed packets.
- **Retransmit:** packets còn lại trong `send_buffer` là unACKed → next timeout sẽ retransmit từ đầu.
- **Verify:** [tests/test_rdt_fault_injection.py#L100-L150](tests/test_rdt_fault_injection.py#L100-L150) - ACK loss test.

---

### Q15: Find Checksum Calculation
**Question:** Tìm CRC16 checksum implementation. Nếu muốn change checksum algorithm, sửa ở đâu?

**Answer & Locator:**
- **File:** [common/rdt_utils.py](common/rdt_utils.py#L1-L30)
- **Function:** `def crc16(data):` → compute CRC16 polynomial.
- **Usage:** [common/RDTHeader.py](common/RDTHeader.py#L70-L100) → `pack()` method tính checksum.
- **Verify:** [tests/test_rdt.py#L50-L100](tests/test_rdt.py#L50-L100) - Checksum round-trip test.
- **Change:** Replace CRC16 polynomial hoặc add new `checksum_algo` parameter; update `pack()`/`unpack()`.

---

### Q16: Find Window Size Limit
**Question:** Tìm code enforce window size ≤4. Nếu muốn change window size → 8, sửa ở đâu?

**Answer & Locator:**
- **File:** [common/rdt_sender.py](common/rdt_sender.py#L50-L80)
- **Constant:** `MAX_WINDOW_SIZE = 4` hoặc `self.window_size = 4`.
- **Enforcement:** `while len(self.send_buffer) >= self.window_size:` → loop cần data send.
- **Waiting:** Sender block nếu window full → chờ ACK để free slot.
- **Change:** Update constant `MAX_WINDOW_SIZE = 8`; verify not breaking assumptions.
- **Verify:** [tests/test_rdt_fault_injection.py#L200-L250](tests/test_rdt_fault_injection.py#L200-L250) - Window exhaustion test.

---

### Q17: Find ABOR Handling
**Question:** Tìm ABOR command xử lý code. Nếu muốn add log "ABOR received", sửa ở đâu?

**Answer & Locator:**
- **TCP side:** [server/command_handler.py](server/command_handler.py#L280-L320) → `def abor_cmd(session, args):`
- **RDT side:** [server/transfer_manager.py](server/transfer_manager.py#L150-L200) → call `sender.abort()` + `receiver.abort()`.
- **RDT cleanup:** [common/rdt_sender.py](common/rdt_sender.py#L300-L320) → `def abort():`
- **Add log:** Insert `logger.info("ABOR received for transfer_id=%s", transfer_id)` trước cleanup.
- **Verify:** [tests/test_rdt.py#L400-L450](tests/test_rdt.py#L400-L450) - ABORT test sẽ thấy log mới.

---

### Q18: Find .part File Cleanup
**Question:** Tìm code xử lý `.part` file. Nếu muốn change extension từ `.part` → `.tmp`, sửa ở đâu?

**Answer & Locator:**
- **File:** [common/file_handler.py](common/file_handler.py#L1-L100) → file naming + cleanup.
- **Pattern:** `temp_filename = filename + ".part"` → search/replace tất cả `.part`.
- **Rename logic:** [common/rdt_receiver.py](common/rdt_receiver.py#L200-L250) → `os.rename(temp_filename, final_filename)`.
- **Cleanup on error:** [server/transfer_manager.py](server/transfer_manager.py#L200-L250) → exception handler xóa `.part`.
- **Change:** Replace `.part` → `.tmp`; run regression [tests/test_e2e_transfer.py](tests/test_e2e_transfer.py) to verify.

---

### Q19: Find Hash Verification Logic
**Question:** Tìm SHA-256 hash được tính + verify. Nếu client send HASH command, reply nằm ở đâu?

**Answer & Locator:**
- **Hash calculation (sender):** [common/rdt_sender.py](common/rdt_sender.py#L180-L240) → compute hash during send.
- **Hash calculation (receiver):** [common/rdt_receiver.py](common/rdt_receiver.py#L150-L200) → compute hash during receive.
- **HASH command reply:** [server/command_handler.py](server/command_handler.py#L350-L380) → `def hash_cmd(session, args):` return `257 hash-value`.
- **Verify:** [tests/test_commands.py#L250-L300](tests/test_commands.py#L250-L300) - HASH command test.
- **Client side:** [client/ftp_client.py](client/ftp_client.py#L200-L250) → compute local hash + compare.

---

### Q20: Find Transfer ID Generation & Tracking
**Question:** Tìm code tạo transfer_id duy nhất + track transfers. Nếu muốn add transfer ID to log, sửa ở đâu?

**Answer & Locator:**
- **Generation:** [server/transfer_manager.py](server/transfer_manager.py#L50-L100) → `transfer_id = uuid.uuid4()`.
- **Tracking dict:** `self.transfers[transfer_id] = TransferContext(...)`.
- **Session binding:** [server/session.py](server/session.py#L100-L150) → `self.current_transfer_id = transfer_id`.
- **Logging:** [server/transfer_manager.py](server/transfer_manager.py#L10-L30) → add `logger.info("Transfer %s started", transfer_id)` in `create_transfer()`.
- **Verify:** [tests/test_transfer_manager.py](tests/test_transfer_manager.py) → check transfer_id in logs.

---

## Part 4: Dry Run Checklist

### A explains TCP/MODE/Command (5 min)
- [ ] Entry point: [server/server.py](server/server.py#L1-L50) main loop
- [ ] Session: [server/session.py](server/session.py#L50-L100)
- [ ] MODE command: [server/command_handler.py](server/command_handler.py#L220-L240)
- [ ] Reply codes: [server/ftp_reply.py](server/ftp_reply.py)

### B explains RDT & Protocol (5 min)
- [ ] Header: [common/RDTHeader.py](common/RDTHeader.py#L1-L100)
- [ ] Sender/Receiver: [common/rdt_sender.py](common/rdt_sender.py) + [common/rdt_receiver.py](common/rdt_receiver.py)
- [ ] Contract: [docs/api-contract.md](docs/api-contract.md)

### C explains Filesystem & Concurrency (5 min)
- [ ] File handler: [common/file_handler.py](common/file_handler.py)
- [ ] Atomic upload: [common/filesystem_service.py](common/filesystem_service.py)
- [ ] Threading: [server/threaded_server.py](server/threaded_server.py)

### Cross-member questions (5 min each)
- [ ] A: "Bagaimana RDT error dipetakan ke FTP reply code?" → B explain + A verify mapping [server/command_handler.py](server/command_handler.py#L400-L450)
- [ ] B: "Mana filesystem lock untuk concurrent upload?" → C show [common/file_handler.py](common/file_handler.py#L200-L250)
- [ ] C: "Bagaimana ABOR signal dikirim via UDP?" → B show [common/RDTHeader.py](common/RDTHeader.py) ABORT command

---

## Part 5: Live Coding Practice Cases

### Case 1: Timeout too short (500ms instead of 1s)
**Scenario:** Transfer fails karena timeout terlalu pendek.
**Live edit:** [common/rdt_context.py](common/rdt_context.py#L30-L60) → change `self.timeout = 0.5` → run test → see failure → change back to 1.

### Case 2: Checksum wrong calculation
**Scenario:** File received tapi hash tidak match.
**Live edit:** [common/rdt_utils.py](common/rdt_utils.py#L1-L30) → introduce bug (e.g. flip bit in CRC) → run [tests/test_rdt.py#L50-L100](tests/test_rdt.py#L50-L100) → see corruption detection fail → fix.

### Case 3: Window size too small (1 packet)
**Scenario:** Transfer sangat lambat; congestion control ketat.
**Live edit:** [common/rdt_sender.py](common/rdt_sender.py#L50-L80) → change `MAX_WINDOW_SIZE = 1` → run [tests/test_rdt.py](tests/test_rdt.py) → slower than window 4 → change back.

### Case 4: PATH TRAVERSAL attack
**Scenario:** Client try `STOR ../../../etc/passwd` → must reject.
**Live edit:** [common/filesystem_service.py](common/filesystem_service.py#L50-L100) → check sandboxing → run [tests/test_filesystem_service.py](tests/test_filesystem_service.py#L200-L250) → verify rejection.

### Case 5: ABOR without transfer
**Scenario:** Client send ABOR khi không có transfer active.
**Live edit:** [server/command_handler.py](server/command_handler.py#L280-L320) → check null transfer_id → return 225 (no transfer) → run [tests/test_commands.py](tests/test_commands.py) → verify.

---

## Sign-off

- [ ] A reviewed Part 1 control understanding
- [ ] B owns Part 1-5 completeness
- [ ] C reviewed Part 2 filesystem understanding
- [ ] Dry run completed with evidence
- [ ] Live coding cases practiced

**Status:** B-F03 ready for oral examination.
