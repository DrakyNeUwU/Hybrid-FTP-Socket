# 8. Concurrency and Integration

**Trạng thái:** Hoàn thành phần Role C; A/B evidence review completed.
**Owner:** C. **Reviewer:** A/B.
**Nguồn:** `../../api-contract.md`, `../../project-status.md`, `tests/test_e2e_transfer.py`.

Server dùng thread-per-client. Mỗi `ClientHandler` sở hữu socket, session và
transfer lifecycle riêng; registry active clients chỉ phục vụ quản lý/quan sát.
Lock của registry được nhả trước cleanup/join. Filesystem dùng per-path lock nên
file khác nhau vẫn transfer song song, còn cùng target không bị interleave.

Role C kiểm chứng ba PASV clients đồng thời: mỗi client có TCP session, remote
filename và download directory riêng; SHA-256 source/server/client khớp. ABOR
hoặc TCP disconnect khi worker đang chờ UDP đều hủy bounded, xóa `.part`, giữ
file cũ và đưa registry về đúng số active clients.

Trong final week, sender được nâng lên Go-Back-N window 4. Sender chỉ giữ tối đa
bốn packets in-flight, nhận ACK tích lũy và retransmit toàn bộ unacknowledged
window từ packet đầu tiên khi timeout. Receiver chỉ commit expected sequence,
re-ACK last contiguous sequence khi nhận duplicate/future packet, nên payload
không bị ghi hai lần. Không global/session lock nào bị giữ khi chờ ACK.

| Scenario | Kết quả | Evidence |
|---|---|---|
| 3 PASV clients | Isolated session/file/download và hash khớp | `../../evidence/week-2.5-three-client.log` |
| ABOR/disconnect | `.part` removed, old target preserved | `../../evidence/week-2.5-e2e-transfer.log` |
| Fault/window | loss, corruption, reorder, exhaustion có retry bounded | `../../evidence/final-week-rdt-gbn-verification.md` |
| LAN PASV/ACTIVE | Hai máy upload/download; hash source/server/client khớp | `../../evidence/final-lan-*-sha256.txt` |

**Evidence final:** focused RDT/fault/transfer/E2E `50 passed in 85.01s`; full
regression `199 passed in 96.72s`. Cần A/B review artifact trước release sign-off.
