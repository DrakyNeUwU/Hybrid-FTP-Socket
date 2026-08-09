# Requirement Acceptance Checklist — Hybrid FTP

**Ngày audit:** 09/08/2026  
**Nguồn requirement:** `planning/Project1_SocketProgramming_2026.md`  
**Trạng thái hiện tại:** acceptance checklist trước nộp; chỉ `docs/project-status.md` là nguồn trạng thái vận hành.

| Requirement / acceptance gate | Trạng thái | Owner cuối | Evidence |
|---|---|---|---|
| TCP control, FTP replies, authentication và session isolation | Done | A | Full WSL2 regression: `189 passed`; `docs/evidence/week-2.5-pytest.log` |
| Commands, filesystem routing và FTP-root safety | Done | A/C | Full regression; filesystem/security tests trong `tests/` |
| UDP payload qua custom RDT, ACK/retry/checksum/FIN | Done | B | RDT và fault-injection tests trong full regression |
| Active/PASV upload/download localhost | Done | A/B/C | `tests/test_e2e_transfer.py`: `5 passed in 18.03s` |
| Binary integrity source/server/client | Done | B/C | `week-2.5-active-sha256.txt`, `week-2.5-pasv-sha256.txt` |
| Multi-client isolation, ABOR/disconnect cleanup | Done | C | FTP E2E log: three PASV clients, ABOR, disconnect |
| CLI progress và server logging có redaction | Done | C | `docs/evidence/week-2.5-cli-logging.log`, screenshots |
| Active/PASV trên hai máy LAN | In progress | C | Cần môi trường hai máy; launcher/hướng dẫn đã có, chưa có run artifact |
| Required final report, task matrix, peer assessment, GenAI log | In progress | B | Report được B tổng hợp; A/C sign-off technical sections |
| Oral/dry-run và Git release hygiene | In progress | B | Chưa có biên bản/evidence dry run |
| Flow/congestion control Excellent | Deferred | C | Không thuộc must-submit gate; chỉ làm sau các gate bắt buộc |

## Gate trước nộp

- [ ] B xác nhận `docs/report.md` không còn placeholder/stale claim; A và C sign-off phần kỹ thuật.
- [ ] Mỗi hàng `Done` có lệnh chạy, log, hash hoặc screenshot truy cập được.
- [ ] Nếu LAN không chạy được, report/status ghi limitation và lý do môi trường thay vì claim pass.
- [ ] `git status --short --branch --untracked-files=all` sạch; không có runtime transfer data ngoài evidence được chủ đích lưu.
- [ ] Full regression được chạy lại gần thời điểm nộp và kết quả ghi vào status/evidence.
