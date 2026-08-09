# Project Status — Hybrid FTP

**Nguồn trạng thái duy nhất:** tài liệu này.
**Ngày cập nhật:** 09/08/2026
**Mục tiêu hiện tại:** hoàn tất *must-submit* trước; C-F01 Excellent chỉ bắt đầu sau khi mọi gate bắt buộc xanh.

## Dashboard hiện tại

| Hạng mục | Trạng thái | Owner cuối | Evidence / blocker |
|---|---|---|---|
| TCP control, parser, session, command lifecycle | Done | A | Full suite và FTP E2E; xem `docs/evidence/week-2.5-pytest.log` |
| UDP/RDT Stop-and-Wait và integrity | Done | B | RDT/fault tests trong full suite; hash Active/PASV khớp |
| Filesystem sandbox, atomic upload, cleanup, concurrency | Done | C | FTP E2E gồm 3 PASV clients, ABOR và disconnect |
| Active/PASV localhost | Done | C | `5 passed in 18.03s`; `docs/evidence/week-2.5-e2e-transfer.log` |
| Active/PASV hai máy LAN | In progress | C | Cần hai máy cùng mạng và evidence thủ công; không phải blocker của localhost E2E |
| Report nộp cuối và acceptance checklist | In progress | B | A/C phải sign-off phần kỹ thuật của mình |
| Oral/dry run và Git release check | In progress | B | Chưa có evidence dry run/release check |
| C-F01 flow/congestion control (Excellent) | Deferred | C | Chỉ thực hiện sau must-submit gates |

## Sự thật đã xác minh

- WSL2 full regression: `python3 -m pytest -q` — **189 passed in 106.91s**; log: `docs/evidence/week-2.5-pytest.log`.
- FTP E2E localhost: `python3 -m pytest tests/test_e2e_transfer.py -v` — **5 passed in 18.03s** (Active, PASV, ba PASV clients, ABOR, disconnect); log: `docs/evidence/week-2.5-e2e-transfer.log`.
- SHA-256 source/server/client khớp cho Active và PASV: `docs/evidence/week-2.5-active-sha256.txt`, `docs/evidence/week-2.5-pasv-sha256.txt`.
- Progress, safe server logging và PASV screenshots: `docs/evidence/week-2.5-cli-logging.log`, `docs/evidence/screenshots/`.

## Quy ước cập nhật mỗi tối

1. Cập nhật dashboard đầu `planning/weekly-plans/tuan-cuoi-ngay-tai-phan-chia.md`: owner, deadline, blocker và evidence link.
2. Cập nhật tài liệu này khi trạng thái thực tế đổi; mọi hàng `Done` phải có evidence.
3. Cập nhật `docs/requirement-checklist.md` và evidence tương ứng; report chỉ được nhận claim đã có ở đây.

Tài liệu tuần và `docs/report-parts/` là lịch sử/nháp, không được dùng để kết luận tiến độ hiện tại.
