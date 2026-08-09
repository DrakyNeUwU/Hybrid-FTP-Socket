# Requirement Acceptance Checklist — Hybrid FTP

**Ngày audit:** 09/08/2026  
**Nguồn requirement:** `planning/Project1_SocketProgramming_2026.md`  
**Trạng thái hiện tại:** acceptance checklist trước nộp; chỉ `docs/project-status.md` là nguồn trạng thái vận hành.

| Requirement / acceptance gate | Trạng thái | Owner cuối | Evidence |
|---|---|---|---|
| TCP control, FTP replies, authentication và session isolation | Done | A | Final WSL2 regression: `199 passed in 96.72s`; `docs/evidence/final-week-rdt-gbn-verification.md` |
| Commands, filesystem routing và FTP-root safety | Done | A/C | Focused C audit: `135 passed in 86.22s`; final regression `199 passed` |
| UDP payload qua custom RDT, ACK/retry/checksum/FIN | Done | B/C | Go-Back-N window 4, START ACK/retry; protocol 27 pass; final suite 199 pass |
| Sliding-window flow control (Excellent) | Done | C/B | `tests/test_rdt.py` proves four in-flight packets and START ACK retry |
| Active/PASV upload/download localhost | Done | A/B/C | Expanded E2E: `6 passed in 22.63s`; final verification artifact |
| Binary integrity source/server/client | Done | B/C | Localhost and LAN SHA-256 logs under `docs/evidence/final-lan-*-sha256.txt` |
| Multi-client isolation, ABOR/disconnect cleanup | Done | C | FTP E2E log: three PASV clients, ABOR, disconnect |
| CLI progress và server logging có redaction | Done | C | `docs/evidence/week-2.5-cli-logging.log`, screenshots |
| Active/PASV trên hai máy LAN | Done | C | PASV/ACTIVE two-machine upload/download; source/server/client SHA-256 match |
| Required final report, task matrix, peer assessment, GenAI log | In progress | B | Report được B tổng hợp; A/C sign-off technical sections |
| Oral/dry-run và Git release hygiene | In progress | B | Chưa có biên bản/evidence dry run |

## Gate trước nộp

- [ ] B xác nhận `docs/report.md` không còn placeholder/stale claim; A và C sign-off phần kỹ thuật.
- [ ] Mỗi hàng `Done` có lệnh chạy, log, hash hoặc screenshot truy cập được.
- [ ] B xác nhận LAN/Go-Back-N evidence đã được review và embed đúng trong report.
- [ ] `git status --short --branch --untracked-files=all` sạch; không có runtime transfer data ngoài evidence được chủ đích lưu.
- [x] Full regression chạy lại: `python3 -m pytest -q` — 199 passed in 96.72s; evidence `docs/evidence/final-week-rdt-gbn-verification.md`.
