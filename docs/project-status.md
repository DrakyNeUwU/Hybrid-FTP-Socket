# Project Status — Hybrid FTP

**Nguồn trạng thái duy nhất:** tài liệu này.
**Ngày cập nhật:** 09/08/2026
**Mục tiêu hiện tại:** hoàn tất *must-submit* trước; C-F01 Excellent chỉ bắt đầu sau khi mọi gate bắt buộc xanh.

## Dashboard hiện tại

| Hạng mục | Trạng thái | Owner cuối | Evidence / blocker |
|---|---|---|---|
| TCP control, parser, session, command lifecycle | Done | A | Full suite và FTP E2E; xem `docs/evidence/week-2.5-pytest.log` |
| UDP/RDT Go-Back-N window 4 và integrity | Done | C/B | START ACK/retry, protocol/fault/E2E; 199 full tests in 96.72s |
| Filesystem sandbox, atomic upload, cleanup, concurrency | Done | C | FTP E2E gồm 3 PASV clients, ABOR và disconnect |
| Active/PASV localhost | Done | C | `5 passed in 18.03s`; `docs/evidence/week-2.5-e2e-transfer.log` |
| Active/PASV hai máy LAN | Done | C | PASV/ACTIVE two-machine upload/download and source/server/client SHA-256 match |
| Report nộp cuối, peer evaluation và acceptance checklist | In progress | B | Technical audit passed; chờ contribution percentage và Git release check |
| Oral preparation và Git release check | In progress | B | Oral pack/locator ready; Git status sạch còn chờ |
| C-F01 Go-Back-N flow/congestion control (Excellent) | Done | C/B | Window 4, cumulative ACK, bounded retry; 199 full tests in 96.72s |

## Sự thật đã xác minh

- Final WSL2 full regression: `python3 -m pytest -q` — **199 passed in 96.72s**; evidence: `docs/evidence/final-week-rdt-gbn-verification.md`.
- Go-Back-N protocol verification: `python3 -m pytest tests/test_rdt.py -q` — **27 passed in 14.76s**; START ACK retry and four-packet in-flight behavior are direct tests.
- Fault + transfer-manager + FTP E2E verification: `python3 -m pytest tests/test_rdt_fault_injection.py tests/test_transfer_manager.py tests/test_e2e_transfer.py -q` — **22 passed in 70.44s**; expanded FTP E2E separately: **6 passed in 22.63s**.
- FTP E2E localhost: `python3 -m pytest tests/test_e2e_transfer.py -v` — **5 passed in 18.03s** (Active, PASV, ba PASV clients, ABOR, disconnect); log: `docs/evidence/week-2.5-e2e-transfer.log`.
- SHA-256 source/server/client khớp cho Active và PASV: `docs/evidence/week-2.5-active-sha256.txt`, `docs/evidence/week-2.5-pasv-sha256.txt`.
- PASV hai máy LAN: source/server/download SHA-256 khớp; `docs/evidence/final-lan-pasv-sha256.txt`.
- ACTIVE hai máy LAN: source/server/download SHA-256 khớp; `docs/evidence/final-lan-active-sha256.txt`.
- Progress và safe server logging: `docs/evidence/week-2.5-cli-logging.log`;
  LAN server/client logs và SHA-256 nằm tại `docs/evidence/final-lan-*`.

## Quy ước cập nhật mỗi tối

1. Cập nhật dashboard đầu `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md`: owner, deadline, blocker và evidence link.
2. Cập nhật tài liệu này khi trạng thái thực tế đổi; mọi hàng `Done` phải có evidence.
3. Cập nhật `docs/requirement-checklist.md` và evidence tương ứng; report chỉ được nhận claim đã có ở đây.

Tài liệu tuần và `docs/report-parts/` là lịch sử/nháp, không được dùng để kết luận tiến độ hiện tại.
