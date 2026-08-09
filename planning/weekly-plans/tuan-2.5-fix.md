# TUẦN 2.5 — CHECKLIST TỔNG HỢP A / B / C

> **Snapshot lịch sử, không phải trạng thái hiện tại.** Xem
> `docs/project-status.md` cho tiến độ, `docs/requirement-checklist.md` cho
> acceptance và `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md` cho final-week tasks.

**Thời gian:** 02/08/2026–08/08/2026  
**Mục tiêu:** chạy được Hybrid FTP thật: TCP control, UDP/RDT data và filesystem
an toàn.
**Nguồn yêu cầu:** `Project1_SocketProgramming_2026.md`
**Quy ước:** `[x]` có test/evidence · `[ ]` chưa làm · `[!]` bị chặn bởi quyết
định hoặc điều kiện bên ngoài.

## Evidence hiện có

| Kiểm chứng | Kết quả | Evidence |
|---|---|---|
| Full regression WSL2 | `[x]` 199 passed in 96.72s | `docs/evidence/final-week-rdt-gbn-verification.md` |
| FTP E2E localhost | `[x]` 5 passed in 18.03s | `docs/evidence/week-2.5-e2e-transfer.log` |
| Integrity Active/PASV | `[x]` SHA-256 nguồn/server/client khớp | `docs/evidence/week-2.5-active-sha256.txt`, `week-2.5-pasv-sha256.txt` |
| Three PASV clients | `[x]` session/file/download riêng, hash khớp | `docs/evidence/week-2.5-three-client.log` |
| ABOR + disconnect | `[x]` `.part` bị xóa, file cũ giữ nguyên | `docs/evidence/week-2.5-e2e-transfer.log` |

## Role A — TCP control, command, session

- [x] Parser TCP chịu được command bị chia/gộp và UTF-8 lỗi.
- [x] USER/PASS, session isolation, RNFR/RNTO reset và validation command.
- [x] PORT anti-bounce, PASV thay socket cũ, reply `150 → 226` và các lỗi
  `425/426/450/550`.
- [x] RETR/STOR/STOU/APPE gọi `TransferManager` qua RDT adapter production.
- [x] Toàn bộ client path đi qua `FilesystemService`.
- [x] `LIST/NLST` trả listing trên TCP control theo đề gốc; UDP/RDT chỉ mang
  actual file payload. Quyết định ghi tại `docs/api-contract.md` §6.1.

**Evidence:** `tests/test_commands.py`, `tests/test_threaded_server.py`,
`tests/test_e2e_transfer.py`, full pytest 189 passed.

## Role B — UDP/RDT

- [x] RDT header có transfer ID, sequence, ACK, flags, length và checksum.
- [x] Stop-and-Wait, retry hữu hạn, FIN, ACK/peer/transfer validation.
- [x] Xử lý loss, corruption, duplicate, out-of-order, cancel và retry exhausted.
- [x] Adapter sender/receiver dùng chung contract `TransferContext`.
- [x] Fault-injection và adapter tests pass trong full pytest.
- [x] Core sender/receiver callback dùng cùng shape; wrapper cũ được giữ tương
  thích ngược.

**Evidence:** `tests/test_rdt.py`, `tests/test_rdt_fault_injection.py`, full
pytest 189 passed.

## Role C — filesystem, concurrency, integration, evidence

- [x] FTP-root confinement: traversal, prefix collision và symlink escape bị chặn.
- [x] STOR atomic bằng `.part`; APPE có per-path lock; STOU tạo tên duy nhất.
- [x] Thread-per-client, session registry, shutdown và cleanup có test.
- [x] Ba client PASV upload/download đồng thời, dữ liệu không lẫn nhau.
- [x] ABOR và TCP disconnect giữa lúc worker chờ UDP: dọn `.part`, giữ file cũ,
  unregister session.
- [x] Active/PASV localhost upload/download và SHA-256 source/server/client.
- [x] Launcher demo LAN: `--host`, `--port`, `--ftp-root`, `--advertise-host`.
- [x] Chạy demo thật giữa hai máy LAN: PASV và ACTIVE upload/download thành
  công; SHA-256 source/server/client khớp. Xem `docs/evidence/final-lan-*.log`
  và `docs/evidence/final-lan-*-sha256.txt`.
- [x] Thu screenshot PASV server log, download progress đúng 0→100% và success
  sau fix `total_bytes`; lưu tại `docs/evidence/screenshots/` theo xác nhận
  của người chạy demo. Screenshot full pytest/Active cũ tiếp tục là evidence
  bổ sung khi chuẩn bị nộp.
- [x] Client demo hiển thị progress upload/download thật; server log connect,
  command đã redact, reply, active-session table, mode/byte count/kết quả.

**Evidence:** `tests/test_filesystem_service.py`, `tests/test_threaded_server.py`,
`tests/test_e2e_transfer.py`, các file trong `docs/evidence/`.

## Dependency cần chốt

| Việc | Owner chính | Phụ thuộc | Trạng thái |
|---|---|---|---|
| Demo hai máy LAN | C | Hai máy cùng mạng, IPv4 server, firewall mở TCP/UDP 2121 | `[x]` PASV/ACTIVE đã thành công, hash khớp |
| Screenshot evidence | C | Terminal chạy demo/test | `[x]` PASV screenshot/server log đã lưu; ACTIVE server screenshot là artifact bổ sung |

## Definition of Done — Tuần 2.5

### Đã đạt ở localhost

- [x] Full pytest pass trên WSL2: 199 tests in 96.72s.
- [x] Active/PASV upload + download thật qua TCP → UDP/RDT → filesystem.
- [x] SHA-256 nguồn/server/client khớp.
- [x] Ba client đồng thời, session và file độc lập.
- [x] ABOR/disconnect cleanup `.part`, socket/session/worker trong test production.
- [x] Filesystem sandbox, atomic upload, APPE lock và STOU unique có test.

### Chưa được phép gọi “hoàn thành toàn bộ”

- [x] Có log/hash demo hai máy LAN cho PASV và ACTIVE; screenshot PASV đã lưu.
- [x] Screenshot PASV progress/server/success đã lưu dưới
  `docs/evidence/screenshots/`.

## Review tổng

**Fact:** Core code đã được kiểm chứng bằng 199 test pass; PASV và ACTIVE đã
được chạy thật qua LAN hai máy với SHA-256 source/server/download bằng nhau.
Role C không còn lỗi cleanup/concurrency hoặc data-path đã biết trong các
scenario đã chạy.

**Còn lại:** A/B review evidence, report và release sign-off. ACTIVE server
log/screenshot có thể thêm cho slide/demo nhưng không phải blocker kỹ thuật.

**Lịch sử thay đổi chi tiết:** `docs/code-change-history.md`
**Contract đang dùng:** `docs/api-contract.md`
**Trạng thái dự án:** `docs/project-status.md`
