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

### A-MODE01 — Chốt contract trước khi code

- [ ] `MODE S` = Stream passthrough; reply chính xác `200 Mode Stream`.
- [ ] `MODE B` = Block encoder/decoder thật; reply chính xác `200 Mode Block`.
- [ ] `MODE C` = Compressed encoder/decoder thật; reply chính xác
  `200 Mode Compressed`.
- [ ] Chỉ cập nhật `Session.transfer_mode` sau command hợp lệ và đã login.
- [ ] Client chỉ cập nhật local mode sau khi nhận reply `200` từ server.
- [ ] `MODE X`/missing argument/unauthenticated trả đúng `501`/`530` và không
  làm thay đổi mode trước đó.
- [ ] Mode là state riêng từng session; không dùng global mutable state.

### A-MODE02 — Thuật toán Stream, Block và Compressed

- [ ] S encoder/decoder trả nguyên byte, không đổi dữ liệu.
- [ ] B dùng block header RFC-style: 1-byte descriptor + 2-byte big-endian
  payload count; block cuối bật EOF descriptor `0x40`.
- [ ] B decoder xử lý header/payload bị chia qua nhiều RDT chunks.
- [ ] C dùng FTP RLE: literal run `0xxxxxxx`, repeated-byte run `10nnnnnn`,
  filler run `11nnnnnn`, và EOF escape `0x00 0x40`.
- [ ] C decoder xử lý control/run bị chia qua nhiều RDT chunks.
- [ ] Empty file, binary `0x00..0xFF`, text, repeated data và file lớn đều
  round-trip không đổi SHA-256.
- [ ] Malformed length, truncated block/run, missing EOF hoặc invalid control
  phải fail hữu hạn; không trả success với output một phần.
- [ ] Không đọc toàn bộ file vào RAM; encoder/decoder hoạt động streaming.

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

- [ ] `TransferContext` hoặc API tương đương mang mode rõ ràng; không đọc mode
  từ global state trong worker.
- [ ] MODE encode xảy ra trước RDT packetization; MODE decode chỉ xảy ra sau
  khi RDT đã kiểm tra checksum, transfer ID, peer và packet order.
- [ ] Không thay đổi canonical RDT header 20 byte, flags, START/ACK, cumulative
  ACK, Go-Back-N window 4, FIN/ABORT hoặc retry policy.
- [ ] C luôn nhận logical decoded bytes; file trong FTP root không chứa block/RLE
  bytes trung gian.
- [ ] `STOR` vẫn commit qua atomic `.part`; malformed MODE stream, timeout,
  ABOR hoặc disconnect phải xóa `.part` và giữ file cũ.
- [ ] `APPE` decode xong trong atomic/shared-lock boundary; hai client append
  cùng file không mất update.
- [ ] `STOU` vẫn tạo tên unique và chỉ publish file sau decode thành công.
- [ ] `RETR` chỉ đọc path đã được C validate; encoder không được bypass sandbox.
- [ ] Progress phân biệt logical file bytes và encoded wire bytes; CLI không
  được vượt 100% hoặc báo complete trước `226`.

### A-MODE04 — Happy-path verification

- [ ] Exact command replies/state tests cho S, B, C, invalid, unauthenticated và
  hai session khác mode.
- [ ] Unit round-trip S/B/C cho empty, one-byte, random binary, text, repeated
  runs và boundary `63/64`, `127/128`, `65535/65536` bytes.
- [ ] PASV upload + download với S/B/C; source/server/client SHA-256 giống nhau.
- [ ] ACTIVE upload + download với S/B/C; source/server/client SHA-256 giống nhau.
- [ ] `STOR`, `RETR`, `STOU`, `APPE` đều đi qua codec production, không mock
  chính encoder/decoder cần chứng minh.
- [ ] Hai client đồng thời dùng mode khác nhau không trộn state hoặc payload.

### A-MODE05 — Failure/reliability verification

- [ ] Packet loss, ACK loss, duplicate, out-of-order và corruption vẫn recover
  qua RDT khi payload là B/C encoded stream.
- [ ] Corrupted MODE frame sau RDT validation hoặc mode mismatch trả `426`,
  không trả `226` và không để file partial.
- [ ] ABOR và TCP disconnect giữa block/run dở dừng worker hữu hạn, đóng UDP và
  cleanup đúng ownership C.
- [ ] Retry exhaustion không deadlock, không giữ shared filesystem lock trong
  lúc chờ UDP ACK.
- [ ] Server stop khi transfer B/C đang chạy vẫn unregister/cleanup idempotent.

### A-MODE06 — Integration review và evidence gate

- [ ] A chạy focused MODE/command/codec tests và lưu exact command/result.
- [ ] A+C chạy production E2E matrix S/B/C × ACTIVE/PASV × upload/download.
- [ ] B xác nhận RDT wire header/flags/retry không đổi.
- [ ] C xác nhận filesystem nhận decoded bytes, atomic cleanup và shared locks
  vẫn pass.
- [ ] Full `python3 -m pytest -q` pass sau tất cả focused/integration tests.
- [ ] A cập nhật `docs/api-contract.md`, control-channel report, limitations,
  `docs/genai-log-a.md`, project status và evidence bằng kết quả thật.
- [ ] Chỉ chuyển A-MODE sang Done sau khi có code locator, test log, hash và
  cross-review record; không đóng bằng static code review.

## Definition of Done — Role A MODE

- [ ] S/B/C có thuật toán production hai chiều, không chỉ reply/state.
- [ ] Tất cả transfer commands và Active/PASV giữ nguyên file SHA-256.
- [ ] Fault/ABOR/disconnect/malformed input không commit file lỗi.
- [ ] Không phá API, RDT wire layout, filesystem sandbox, atomic `.part`, shared
  locks, concurrency và logging của Role C.
- [ ] Focused + integration + full regression đều pass và có evidence thật.
- [ ] Report mô tả đúng implementation cuối, không claim trước evidence.

## Phần ngoài scope Role C

Ngoài integration review nêu trên, Role C không implement thay A. Authentication,
STAT/HELP/STOU, TCP client framing, legacy A modules và MODE codecs thuộc Role A.
Session Structure, contribution percentage và GenAI historical backfill cũng
không được tự động đóng trong checklist này.
