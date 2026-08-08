# Project Status — Hybrid FTP

**Ngày cập nhật:** 08/08/2026
**Phạm vi:** kiểm tra Role A và trạng thái tích hợp A/B/C

## Tóm tắt

Role A đã hoàn thành phần lớn TCP control, parser, authentication, session,
filesystem delegation và transfer orchestration. Contract A–B hiện đã được
đồng bộ bằng `TransferContext`, và RDT unit/fault tests đã chạy pass. Tuy
nhiên, Active/PASV qua server FTP thật vẫn cần test end-to-end.

## Tiến độ theo nhóm

| Hạng mục | Trạng thái | Ghi chú |
|---|---:|---|
| TCP framing và command parser | 100% | Đã xử lý command bị chia/gộp và UTF-8 lỗi |
| Authentication và session isolation | 100% | Có USER/PASS reset, session riêng |
| FTP command dispatch/reply | 90% | Có command chính; cần thêm lifecycle/integration evidence |
| Filesystem delegation | 90% | Client path đi qua `FilesystemService`; cần test security đầy đủ |
| Transfer orchestration | 95% | Có worker, result, cancel, context và guard transfer chồng nhau |
| Active/PASV endpoint | 95% | Localhost pass; LAN launcher có bind/advertise host, chờ demo khác máy |
| UDP/RDT integration | 90% | RDT + FTP e2e localhost, SHA-256 source/server/client đã pass |
| ABOR/disconnect cleanup | 100% | Production PASV tests dọn `.part`, giữ file cũ và unregister session |
| CLI/server observability | 100% | Progress thật, command redact, transfer lifecycle và active-session table |
| Automated verification | 100% | Full WSL2 pytest evidence: 189 passed in 106.91s |
| Demo/evidence/report | 95% | Có E2E, concurrent, cleanup, logging và PASV screenshots; còn LAN |

## Việc đã làm trong vòng cập nhật này

- Thêm chống chạy nhiều transfer trên cùng một session.
- Khi transfer đang chạy, `RETR`, `STOR`, `STOU`, `APPE` trả mã `450` thay vì
  ghi đè state của worker trước.
- Thêm test cho transfer chồng nhau.
- Ghi lại rõ các phần còn phụ thuộc Role B/C, không đánh dấu pass chỉ dựa trên
  unit test.
- Đồng bộ `TransferManager` với `TransferContext` theo `docs/api-contract.md`.
- Dùng adapter RDT canonical trong `common/`; `server/rdt_adapter.py` chỉ còn
  compatibility export.
- Sửa validation flags/length, peer/transfer ACK, out-of-order, checksum,
  retry hữu hạn và log không phụ thuộc encoding tiếng Việt.
- Bổ sung integration test TCP control → UDP/RDT → filesystem cho STOR/RETR
  ở cả Active và PASV, kiểm tra SHA-256 ở nguồn/server/client.

## Việc tiếp theo theo owner

### Role A

- Viết integration test cho TCP → TransferManager → UDP → filesystem.
- Chốt lifecycle socket sau transfer và test ABOR/disconnect khi đang chờ UDP.
- Thống nhất data-channel behavior của LIST/NLST.

### Role B

- Chốt peer/transfer validation, FIN/ACK, timeout hữu hạn và fault injection.
- Cung cấp adapter production ổn định theo contract của `TransferManager`.

### Role C

- Nếu có thời gian, chạy demo khác máy/LAN.
- Với demo LAN PASV, dùng `--advertise-host <IPv4-LAN-server>` để client nhận
  đúng endpoint UDP; hướng dẫn có trong `README.md`.

## Bằng chứng kiểm tra

- Pass: `python -m unittest tests.test_command_parser tests.test_session tests.test_commands -q`
-  — 52 tests.
- Pass: `python -m unittest tests.test_rdt.TestRDTHeader tests.test_rdt.TestRDTProtocolLogic -v`
  — 21 tests.
- Pass: `python -m unittest tests.test_rdt_fault_injection.TestRDTFaultInjection tests.test_rdt_fault_injection.TestRDTAdapterFaultInjection -q`
  — 14 tests.
- Pass: `python -m unittest tests.test_e2e_transfer -v`
  — 2 test: Active và PASV upload/download, SHA-256 khớp.
- Demo thủ công pass: `python -m client.demo_transfer .\demo.bin --remote
  demo-active.bin --mode ACTIVE` trả `220` và thông báo upload + download Active
  thành công.
- Evidence hash đã lưu cho cả hai mode tại `docs/evidence/`:
  `week-2.5-active-sha256.txt` và `week-2.5-pasv-sha256.txt`.
- Pass trên WSL2: `python3 -m pytest -q` — **189 passed in 106.91s**.
  Full output được lưu tại `docs/evidence/week-2.5-pytest.log`.
- Pass trên WSL2: `python3 -m pytest
  tests/test_e2e_transfer.py::TestEndToEndPasvTransfer::test_three_pasv_clients_transfer_independently -v`
  — **1 passed in 5.34s**. Log: `docs/evidence/week-2.5-three-client.log`.
- Pass trên WSL2: `python3 -m pytest tests/test_e2e_transfer.py -v` — **5
  passed in 18.03s** (Active, PASV, 3 client PASV, ABOR, disconnect). Log:
  `docs/evidence/week-2.5-e2e-transfer.log`.
- Chưa xác minh: demo trên hai máy/mạng khác nhau. Demo thủ công Active và
  PASV localhost đã được người chạy demo xác nhận thành công.
- Pass sau bổ sung launcher LAN: `python3 -m server.threaded_server --help`
  và `python3 -m pytest tests/test_threaded_server.py tests/test_e2e_transfer.py -q`
  — **10 passed in 21.56s**.
- Pass sau progress/logging: `python3 -m pytest tests/test_commands.py
  tests/test_threaded_server.py tests/test_e2e_transfer.py tests/test_cli_display.py -q`
  — **62 passed in 22.16s**. Log: `docs/evidence/week-2.5-cli-logging.log`.
- Progress RETR verified: `python3 -m pytest tests/test_e2e_transfer.py -q` —
  **5 passed in 17.61s**; each download callback reports the validated total
  file size.
- Manual PASV progress/server/success screenshots were saved under
  `docs/evidence/screenshots/` (user confirmation, 08/08/2026).
