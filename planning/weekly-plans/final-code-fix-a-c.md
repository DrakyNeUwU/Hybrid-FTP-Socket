# Final Code Fix A/C — C Verified, A MODE Handoff 10/08/2026

**Nguồn chuẩn:** `planning/reference/Project1_SocketProgramming_2026.md` và
`docs/api-contract.md`. **Status chuẩn:** `docs/project-status.md`.

Role C dùng file này để ghi phần đã verify. Role A dùng phần handoff bên dưới để
tự implement MODE S/B/C. Các ô Role A giữ nguyên chưa tick cho đến khi có code,
test và evidence do A thực hiện; C chỉ review integration boundary.

## Nguyên tắc

- [x] Role C sở hữu filesystem boundary, shared locks, threaded server,
  integration và evidence.
- [x] Không thay đổi RDT wire layout trong scope Role C.
- [x] Task chỉ được tick Done khi có test/log/hash thật.
- [x] Không claim hoàn thành task Role A từ code do Role C/AI viết.

## Role C checklist

### C-FIX01 — Shared filesystem concurrency

- [x] `FTPServer` sở hữu một `FilesystemService`.
- [x] Mọi client handler dùng chung path-lock registry.
- [x] Handler identity test pass.
- [x] Concurrent same-file APPE không mất update.

### C-FIX02 — Thread/session lifecycle

- [x] Start handler trước khi ghi active-session snapshot.
- [x] Cleanup bounded và idempotent.
- [x] Active session report `alive=True` trong test.

### C-FIX03 — Integration regression

- [x] Active/PASV transfer path đã được rà.
- [x] RDT, filesystem và same-file concurrency tests pass.
- [x] Focused Role C sau rollback: 24 passed trong 33.80s.
- [x] Full regression sau rollback: 205 passed trong 103.08s.

### C-FIX04 — Documentation và evidence

- [x] API contract mô tả đúng RDT header và resource ownership của C.
- [x] Report §7 dùng evidence thật.
- [x] Đồng bộ tài liệu hiện hành với việc Role A được trả lại owner.
- [ ] Git release check sạch sau commit.

## Definition of Done — Role C

### Code

- [x] Shared filesystem service được dùng trong production path.
- [x] Path validation, binary I/O, atomic `.part` và shared lock được giữ.
- [x] Active/PASV integration không phá RDT wire layout.
- [x] Cleanup khi ABOR/disconnect/server stop là bounded và idempotent.

### Test và evidence

- [x] Focused filesystem/threading/transfer/E2E: 24 passed trong 33.80s.
- [x] Full `python3 -m pytest -q`: 205 passed trong 103.08s.
- [x] Evidence ghi đúng command, result và scope Role C.

### Documentation và release

- [x] Status/report không còn claim code Role A đã hoàn thành trong đợt fix này.
- [x] `git diff --check` pass.
- [ ] Git worktree sạch sau commit trước khi đánh dấu release-ready.

## Role A handoff — Functional MODE S/B/C

**Owner implementation:** Role A. **Integration reviewer:** Role C.
**RDT contract reviewer:** Role B.  
**Requirement:** `Project1_SocketProgramming_2026.md` §2.2 `MODE {S|B|C}`.
**Algorithm reference:** RFC 959 §3.4 Transmission Modes.

> Status 10/08/2026: Role A đã implement đầy đủ S/B/C trên production path và
> self-verify. Evidence thật ở cuối mục này. Các ô chờ confirm B/C và release
> git vẫn giữ unchecked cho role sở hữu.

### A-MODE01 — Chốt contract trước khi code

- [x] `MODE S` = Stream passthrough; reply chính xác `200 Mode Stream`.
  (`server/command_handler.py` `mode_cmd`; `tests/test_commands.py`).
- [x] `MODE B` = Block encoder/decoder thật; reply chính xác `200 Mode Block`.
- [x] `MODE C` = Compressed encoder/decoder thật; reply chính xác
  `200 Mode Compressed`.
- [x] Chỉ cập nhật `Session.transfer_mode` sau command hợp lệ và đã login.
- [x] Client chỉ cập nhật local mode sau khi nhận reply `200` từ server.
  (`client/ftp_client.py` `_ensure_transfer_mode`).
- [x] `MODE X`/missing argument/unauthenticated trả đúng `501`/`530` và không
  làm thay đổi mode trước đó.
- [x] Mode là state riêng từng session; không dùng global mutable state.

### A-MODE02 — Thuật toán Stream, Block và Compressed

- [x] S encoder/decoder trả nguyên byte, không đổi dữ liệu
  (`common/mode_codec.py` `encode_chunks`/`decode_chunks` MODE_STREAM).
- [x] B dùng block header RFC-style: 1-byte descriptor + 2-byte big-endian
  payload count; block cuối bật EOF descriptor `0x40`.
- [x] B decoder xử lý header/payload bị chia qua nhiều RDT chunks.
- [x] C dùng FTP RLE: literal run `0xxxxxxx`, repeated-byte run `10nnnnnn`,
  filler run `11nnnnnn`, và EOF escape `0x00 0x40`.
- [x] C decoder xử lý control/run bị chia qua nhiều RDT chunks.
- [x] Empty file, binary `0x00..0xFF`, text, repeated data và file lớn đều
  round-trip không đổi SHA-256.
- [x] Malformed length, truncated block/run, missing EOF hoặc invalid control
  phải fail hữu hạn; không trả success với output một phần.
- [x] Không đọc toàn bộ file vào RAM; encoder/decoder hoạt động streaming.

### A-MODE03 — Production-path integration với Role C

Upload production path bắt buộc:

```text
FTPClient file chunks → A MODE encoder → B RDT sender → UDP
→ B RDT receiver/order/checksum → A MODE decoder
→ C FilesystemService.store/append/store_unique
```

Download production path bắt buộc:

```text
C FilesystemService.read_chunks → A MODE encoder → B RDT sender → UDP
→ B RDT receiver/order/checksum → A MODE decoder → FTPClient destination
```

- [x] `TransferContext` hoặc API tương đương mang mode rõ ràng; không đọc mode
  từ global state trong worker. (`server/transfer_manager.py` lưu
  `transfer_mode` trong `TransferContext`; codec chọn qua `_mode_for(session)`).
- [x] MODE encode xảy ra trước RDT packetization; MODE decode chỉ xảy ra sau
  khi RDT đã kiểm tra checksum, transfer ID, peer và packet order.
  (`_send` bọc `encode_chunks` trước `RDTSenderAdapter`; upload/append/stou
  bọc `decode_chunks` quanh `RDTReceiverAdapter.receive`).
- [x] Không thay đổi canonical RDT header 20 byte, flags, START/ACK, cumulative
  ACK, Go-Back-N window 4, FIN/ABORT hoặc retry policy. (Wire layout giữ
  nguyên; chỉ thứ tự progress-cb/ACK trong `receive_chunks_rdt` đổi để `total`
  logical có trước chunk đầu — không đổi packet format. Chờ B confirm.)
- [x] C luôn nhận logical decoded bytes; file trong FTP root không chứa block/RLE
  bytes trung gian.
- [x] `STOR` vẫn commit qua atomic `.part`; malformed MODE stream, timeout,
  ABOR hoặc disconnect phải xóa `.part` và giữ file cũ.
- [x] `APPE` decode xong trong atomic/shared-lock boundary; hai client append
  cùng file không mất update.
- [x] `STOU` vẫn tạo tên unique và chỉ publish file sau decode thành công.
- [x] `RETR` chỉ đọc path đã được C validate; encoder không được bypass sandbox.
- [x] Progress phân biệt logical file bytes và encoded wire bytes; CLI không
  được vượt 100% hoặc báo complete trước `226`.
  `send_file_rdt` đếm logical bytes từ `read_file_chunks` trước encoder;
  `receive_file_rdt` đếm bytes sau decoder; total = kích thước logical từ
  START header. (`common/rdt_sender.py`, `common/rdt_receiver.py`;
  assert tại `tests/test_e2e_transfer.py::test_mode_progress_counts_logical_bytes`:
  `done <= total` cho mọi event và event cuối `== len(payload)` với B và C.)

### A-MODE04 — Happy-path verification

- [x] Exact command replies/state tests cho S, B, C, invalid, unauthenticated và
  hai session khác mode. (`tests/test_commands.py`).
- [x] Unit round-trip S/B/C cho empty, one-byte, random binary, text, repeated
  runs và boundary `63/64`, `127/128`, `65535/65536` bytes.
  (`tests/test_mode_codec.py::test_boundary_sizes`).
- [x] PASV upload + download với S/B/C; source/server/client SHA-256 giống nhau.
  (`tests/test_e2e_transfer.py::test_pasv_mode_matrix_preserves_sha256`).
- [x] ACTIVE upload + download với S/B/C; source/server/client SHA-256 giống nhau.
  (`tests/test_e2e_transfer.py::test_active_mode_matrix_preserves_sha256`).
- [x] `STOR`, `RETR`, `STOU`, `APPE` đều đi qua codec production, không mock
  chính encoder/decoder cần chứng minh.
- [x] Hai client đồng thời dùng mode khác nhau không trộn state hoặc payload.
  (`tests/test_e2e_transfer.py::test_two_clients_different_modes_do_not_mix`).

### A-MODE05 — Failure/reliability verification

- [x] Packet loss, ACK loss, duplicate, out-of-order và corruption vẫn recover
  qua RDT khi payload là B/C encoded stream.
  (`tests/test_rdt_fault_injection.py`:
  `test_adapter_mode_loss_and_corruption_recovery`,
  `test_adapter_mode_ack_loss_recovery`,
  `test_adapter_mode_duplicate_recovery`,
  `test_adapter_mode_out_of_order_recovery`,
  `test_adapter_mode_clean_sha256`. NetworkProxy inject drop/corrupt/ACK-loss/
  duplicate/out-of-order.)
- [x] Corrupted MODE frame sau RDT validation hoặc mode mismatch trả `426`,
  không trả `226` và không để file partial.
  (`tests/test_transfer_manager.py::test_malformed_mode_stream_fails_atomic_426`).
- [x] ABOR và TCP disconnect giữa block/run dở dừng worker hữu hạn, đóng UDP và
  cleanup đúng ownership C. (`tests/test_transfer_manager.py`:
  `test_cancel_mid_block_stream_preserves_old_file` (B, cancel giữa stream →
  426, giữ file cũ, không `.part`), `test_disconnect_mid_compressed_stream_preserves_old_file`
  (C, disconnect giữa stream → 426, giữ file cũ, không `.part`);
  điều khiển/cleanup thật tại `tests/test_e2e_transfer.py`:
  `test_abor_waiting_upload_removes_temporary_file`,
  `test_disconnect_waiting_upload_removes_temporary_file`.)
- [x] Retry exhaustion không deadlock, không giữ shared filesystem lock trong
  lúc chờ UDP ACK. (`tests/test_rdt_fault_injection.py::test_max_retry_exhausted_is_finite`;
  lock chỉ được acquire bên trong `_atomic_upload`/`_atomic_append` sau khi
  receive đã trả, không nằm trong lúc chờ UDP.)
- [x] Server stop khi transfer B/C đang chạy vẫn unregister/cleanup idempotent.
  (`tests/test_e2e_transfer.py::test_server_stop_during_mode_b_upload_cleanup`
  — stop server giữa B-upload thật: worker dừng hữu hạn, `.part` bị xóa, file
  không được commit; plus `tests/test_threaded_server.py::test_server_stop_cleanup`,
  `test_stop_with_connected_client_does_not_deadlock`.)

### A-MODE06 — Integration review và evidence gate

- [x] A chạy focused MODE/command/codec tests và lưu exact command/result.
- [ ] A+C chạy production E2E matrix S/B/C × ACTIVE/PASV × upload/download.
- [ ] B xác nhận RDT wire header/flags/retry không đổi.
- [ ] C xác nhận filesystem nhận decoded bytes, atomic cleanup và shared locks
  vẫn pass.
- [x] Full `python3 -m pytest -q` pass sau tất cả focused/integration tests.
- [x] A cập nhật `docs/api-contract.md`, control-channel report, limitations,
  `docs/genai-log-a.md`, project status và evidence bằng kết quả thật.
  (Đã cập nhật: `docs/api-contract.md` §6.3 + changelog,
  `docs/report-parts/technical/04-control-channel.md` §4.3–4.4,
  `docs/report-parts/submission/10-testing-results.md`,
  `docs/report-parts/submission/12-limitations-future-work.md`,
  `docs/report.md` §8–9, `docs/genai-log-a.md` entry 10/08,
  `docs/project-status.md`, `docs/requirement-checklist.md`,
  `docs/evidence/final-code-fix-verification.md`.)
- [ ] Chỉ chuyển A-MODE sang Done sau khi có code locator, test log, hash và
  cross-review record; không đóng bằng static code review.

## Definition of Done — Role A MODE

- [x] S/B/C có thuật toán production hai chiều, không chỉ reply/state.
- [x] Tất cả transfer commands và Active/PASV giữ nguyên file SHA-256.
- [x] Fault/ABOR/disconnect/malformed input không commit file lỗi.
- [x] Không phá API, RDT wire layout, filesystem sandbox, atomic `.part`, shared
  locks, concurrency và logging của Role C.
- [x] Focused + integration + full regression đều pass và có evidence thật.
- [x] Report mô tả đúng implementation cuối, không claim trước evidence.

## Evidence — Role A implementation (đã chạy 10/08/2026)

Code locator:

- `common/mode_codec.py` — normalize_mode, encode_chunks/decode_chunks,
  block_encode/block_decode, compressed_encode/compressed_decode,
  WIRE_CHUNK_SIZE=1024, `_batch_wire`.
- `server/command_handler.py` — `mode_cmd` (200/501/530, cập nhật
  `session.transfer_mode`).
- `server/transfer_manager.py` — TransferContext.transfer_mode; `_send` encode
  trước RDT; upload/append/upload_unique decode sau RDT; atomic `.part` giữ nguyên.
- `client/ftp_client.py` — `transfer_mode`, `_negotiated_mode`, `_ensure_transfer_mode`,
  send/receive_file_rdt qua codec; progress đếm logical bytes.
- `client/demo_transfer.py` — `--mode` và command `MODE` với user.
- `common/rdt_sender.py` — `send_file_rdt`: progress đếm logical bytes trước
  encoder (RDT wire layout không đổi).
- `common/rdt_receiver.py` — `receive_file_rdt`: public progress đếm logical
  bytes sau decoder; thứ tự progress-cb/ACK/yield chỉnh để total có trước chunk
  đầu (không đổi wire layout; checksum/START/ACK/order giữ nguyên).

Command và result:

```text
$ python3 -m pytest tests/test_mode_codec.py tests/test_commands.py -q
83 passed, 338 subtests passed in 0.24s

$ python3 -m pytest tests/test_mode_codec.py -q
29 passed, 338 subtests passed in 0.12s

$ python3 -m pytest tests/test_transfer_manager.py -q
12 passed in 0.12s
  (gồm block/compressed decode trên store/append/STOU, malformed→426 atomic,
  cancel và disconnect giữa block/run giữ file cũ không để `.part`)

$ python3 -m pytest tests/test_rdt_fault_injection.py -q
19 passed, 11 subtests passed in 71.99s
  (B/C payloads dưới loss, corruption, ACK-loss, duplicate, out-of-order)

$ python3 -m pytest tests/test_e2e_transfer.py -q
13 passed, 8 subtests passed in 77.13s
  (gồm PASV/ACTIVE matrix S/B/C, STOU/APPE block, hai client khác mode,
  progress logical bytes B/C không vượt 100%, server stop giữa B-upload)

$ python3 -m pytest -q
256 passed, 357 subtests passed in 167.08s
```

Focused Role A trước đợt code này ghi nhận 24 passed (C-FIX03); sau khi Role A
implement MODE, full regression là **256 passed** với 357 subtests, không có
failure. Các ô chờ xác nhận của Role B/C và release git vẫn để unchecked theo
nguyên tắc cross-review ở đầu file.

## Phần ngoài scope Role C

Ngoài integration review nêu trên, Role C không implement thay A. Authentication,
STAT/HELP/STOU, TCP client framing, legacy A modules và MODE codecs thuộc Role A.
Session Structure, contribution percentage và GenAI historical backfill cũng
không được tự động đóng trong checklist này.
