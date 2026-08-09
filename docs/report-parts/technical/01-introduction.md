# 1. Introduction

**Trạng thái:** Hoàn thành phần Role C; chờ A review và B tổng hợp report.
**Owner:** C. **Reviewer:** A.
**Nguồn:** `../../../planning/Project1_SocketProgramming_2026.md`, `../../requirement-checklist.md`.

Hybrid FTP tách hai trách nhiệm mạng: TCP mang command, FTP reply và session;
UDP mang payload file qua Reliable Data Transfer (RDT) tự cài đặt. Thiết kế này
giữ control flow rõ ràng nhưng vẫn yêu cầu RDT xử lý mất gói, lỗi checksum,
duplicate, out-of-order, timeout và kết thúc transfer.

Role C chịu trách nhiệm boundary filesystem, server thread/session isolation,
integration TCP–UDP–filesystem, observability và final evidence. Trong final
week, Role C hoàn tất Go-Back-N bounded window 4, START ACK/retry hữu hạn,
two-machine LAN Active/PASV và regression sau cùng. Không thay đổi FTP command
grammar, RDT header wire layout hoặc ownership reply của Role A.

| Mức độ | Capability đã chứng minh | Evidence |
|---|---|---|
| Advanced | Active/PASV upload/download, sandbox, atomic upload, concurrent clients, cleanup | FTP E2E và LAN logs dưới `docs/evidence/` |
| Excellent | Custom RDT, checksum/retry, Go-Back-N window 4, end-to-end SHA-256 | `final-week-rdt-gbn-verification.md` |

**Evidence chính:** Full WSL2 regression `199 passed in 96.72s`; FTP E2E mở rộng
`6 passed in 22.63s`; LAN PASV và ACTIVE đều có SHA-256 source/server/client
khớp. Xem `../../evidence/final-week-rdt-gbn-verification.md`,
`../../evidence/final-lan-pasv-sha256.txt` và
`../../evidence/final-lan-active-sha256.txt`.

**Limitation còn lại:** `MODE B/C` vẫn trả `502` vì chưa có data path được
requirement/team chốt; B cần review wire contract trước release sign-off.
