# Report Fix A/C — Role A MODE S/B/C + Reliability Hardening (10/08/2026)

Báo cáo riêng cho đợt fix A/C: tổng hợp implementation, verification và
cross-review status của Role A. Nguồn chuẩn:
`planning/weekly-plans/final-code-fix-a-c.md`, `docs/api-contract.md`,
`docs/project-status.md`.

## 1. Scope

Role A implement functional `MODE S/B/C` trên production path (RFC 959 §3.4,
`Project1_SocketProgramming_2026.md` §2.2), kèm hardening reliability:
duplicate/out-of-order recovery, cancel/disconnect giữa block/run, và server
stop mid-transfer. Role C giữ filesystem/atomic `.part`/shared locks/threaded
server; Role B giữ RDT wire layout 20-byte.

## 2. Implementation

### 2.1 Codec — `common/mode_codec.py`

- `normalize_mode`, `encode_chunks`/`decode_chunks` dispatcher.
- Block (RFC 959): 1-byte descriptor + 2-byte big-endian count; block cuối bật
  EOF descriptor `0x40`.
- Compressed (FTP RLE): literal run `0xxxxxxx`, repeated-byte run `10nnnnnn`,
  filler run `11nnnnnn`, EOF escape `0x00 0x40`.
- Streaming generators (không đọc toàn file vào RAM); `_batch_wire` giữ wire
  chunk ≤ `WIRE_CHUNK_SIZE` = 1024 bytes.

### 2.2 Command — `server/command_handler.py` `mode_cmd`

- `MODE S/B/C` → `200 Mode Stream/Block/Compressed`.
- Invalid/missing argument → `501`; unauthenticated → `530`; không đổi mode cũ.
- Chỉ cập nhật `session.transfer_mode` (per-session, không global mutable state).

### 2.3 Production integration — `server/transfer_manager.py`

- `TransferContext.transfer_mode`; encode trước RDT send, decode sau RDT receive.
- `STOR`/`APPE`/`STOU` giữ atomic `.part` và shared locks; decode lỗi → `426`
  không để file partial, file cũ giữ nguyên.

### 2.4 Client — `client/ftp_client.py`, `client/demo_transfer.py`

- `transfer_mode`, `_negotiated_mode`, `_ensure_transfer_mode` (chỉ đổi local
  mode sau reply `200`); codec trên send/receive.
- CLI `--transfer-mode` + command `MODE` với user.

### 2.5 RDT progress — `common/rdt_sender.py`, `common/rdt_receiver.py`

- Progress đếm logical (decoded) bytes để CLI không vượt 100% và không báo
  complete trước `226`.
- Wire layout 20-byte header, flags, START/ACK, Go-Back-N window 4, FIN/ABORT,
  retry policy không đổi; chỉ thứ tự progress-cb/ACK trong receiver đổi để
  total có trước chunk đầu.

## 3. Verification (chạy thật 10/08/2026)

| Suite | Command | Result |
|---|---|---|
| Codec + command | `pytest tests/test_mode_codec.py tests/test_commands.py -q` | 83 passed, 338 subtests (0.27s) |
| Codec only | `pytest tests/test_mode_codec.py -q` | 29 passed, 338 subtests (0.12s) |
| Transfer manager | `pytest tests/test_transfer_manager.py -q` | 12 passed (0.06s) |
| RDT fault B/C | `pytest tests/test_rdt_fault_injection.py -q` | 19 passed, 11 subtests (71.99s) |
| E2E matrix | `pytest tests/test_e2e_transfer.py -q` | 13 passed, 8 subtests (77.13s) |
| Full regression after C production review | `pytest -q` | 271 passed, 357 subtests (192.88s) |

Baseline lịch sử: focused Role A pre-MODE (C-FIX03) = **24 passed / 33.80s**.
Re-run hiện tại của 4-file set đó = **39 passed, 8 subtests / 80.48s** vì
transfer-manager tăng 10→12 và e2e tăng 12→13.

## 4. Reliability verification

- Loss, corruption, ACK-loss, duplicate, out-of-order đều recover qua RDT khi
  payload là B/C encoded stream (`tests/test_rdt_fault_injection.py`).
- Malformed MODE stream sau RDT validation → `426`, không `226`, không file
  partial (`test_malformed_mode_stream_fails_atomic_426`).
- Cancel (B) và TCP disconnect (C) giữa block/run → worker dừng hữu hạn, giữ
  file cũ, không để `.part` (`test_cancel_mid_block_stream_preserves_old_file`,
  `test_disconnect_mid_compressed_stream_preserves_old_file`).
- Server stop giữa B-upload → cleanup unregister idempotent, `.part` bị xóa,
  file không commit (`test_server_stop_during_mode_b_upload_cleanup`).
- Progress logical bytes ≤100%; event cuối `== len(payload)` cho B và C.

## 5. Documentation & evidence sync

Đã đồng bộ số liệu cuối (256/357/167.08s, 19/11, 12, 13/8) vào:

- `docs/api-contract.md` §6.3 + changelog
- `docs/report-parts/technical/04-control-channel.md` §4.3–4.4
- `docs/report-parts/submission/10-testing-results.md`
- `docs/report-parts/submission/12-limitations-future-work.md`
- `docs/report.md` §8–9
- `docs/project-status.md`, `docs/requirement-checklist.md`
- `docs/genai-log-a.md`, `docs/evidence/final-code-fix-verification.md`

## 6. Cross-review status

- [x] A self-verify: focused + full regression pass, evidence thật.
- [x] Report mô tả đúng implementation cuối, không claim trước evidence
      (audit 10/08/2026; fix §8 Final Evidence table + thêm MODE row).
- [ ] A+C chạy production E2E matrix thật (S/B/C × ACTIVE/PASV × upload/download).
- [ ] B xác nhận RDT wire header/flags/retry không đổi sau MODE.
- [ ] C xác nhận filesystem nhận decoded bytes, atomic cleanup, shared locks pass.
- [ ] Git release check sạch.

## 7. Kết luận

Full regression **271 passed, 357 subtests, không failure** sau khi C sửa silent
MODE mismatch, client atomic download, TCP framing và command gaps. RDT header
vẫn 20 byte; START payload thêm MODE/TYPE cần B review. Filesystem sandbox,
atomic `.part`, shared locks và concurrency của Role C giữ nguyên. Chờ screenshot
Role A, cross-review B và git release để đóng release.
